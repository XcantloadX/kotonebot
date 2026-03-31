import React from 'react';
import { FormGroup, InputGroup, Button, Tooltip } from '@blueprintjs/core';
import { useTranslation } from 'react-i18next';
import { useAppStore } from '../editor/state';
import { PropValue, VariantPolicy } from '../model/metaV2';
import { EditorPropSchema } from '../model/prefabSchema';
import { COMMAND_ID, executeCommand } from '../editor/commands';
import { useSymbolIndexStore } from '../editor/symbolIndexStore';
import { getEditorForType } from './properties/PropertyEditorRegistry';
import { OverridableField } from './components/OverridableField';
import { SegmentedControl, SegmentedOption } from './components/SegmentedControl';
import { toaster } from './toaster';
import { HelpIcon } from './components/HelpIcon';
import { useProjectInfoStore } from '../app/projectInfoStore';
import { AutoCompleteInput } from './components/AutoCompleteInput';

export const RightProperties: React.FC = () => {
  const { t } = useTranslation();

  const VARIANT_POLICY_OPTIONS: readonly SegmentedOption<VariantPolicy>[] = [
    { label: t('rightProperties.variantPolicyInherit'), value: 'inherit' },
    { label: t('rightProperties.variantPolicyRequire'), value: 'require' },
    { label: t('rightProperties.variantPolicyExclude'), value: 'exclude' },
  ];
  const commandContext = React.useMemo(() => ({ ui: {} }), []);
  const { activeDocumentId, documents, prefabSchema, updateMeta, setMode } = useAppStore();
  const symbols = useSymbolIndexStore(s => s.symbols);
  const [nameDraft, setNameDraft] = React.useState<string>('');
  const projectVariants = useProjectInfoStore((state) => state.data?.variant?.variants ?? []);

  const activeDoc = activeDocumentId ? documents[activeDocumentId] : null;
  const activeMeta = activeDoc?.meta;
  const selection = activeDoc?.selection;
  const defId = selection?.definitionId ?? null;
  const definition = activeMeta && defId ? activeMeta.data.definitions[defId] : null;

  const nameSuggestions = React.useMemo(() => {
    const seen = new Set<string>();
    for (const s of symbols) {
      if (s.name) seen.add(s.name);
    }
    return Array.from(seen).sort();
  }, [symbols]);
  React.useEffect(() => {
    setNameDraft(definition?.name || '');
  }, [activeMeta?.path, defId, definition?.name]);

  if (!activeMeta || !selection || !defId) {
    return <div style={{ padding: 10, color: '#8a9ba8' }}>{t('status.noSelection')}</div>;
  }

  if (!definition) {
      return <div style={{ padding: 10, color: '#8a9ba8' }}>{t('status.definitionNotFound')}</div>;
  }

  const isVariantPrefab = definition.type === "prefab" && !!definition.variant;
  const currentName = definition.name || '';
  const trimmedNameDraft = nameDraft.trim();
  const hasPendingNameChange = !isVariantPrefab && trimmedNameDraft !== currentName;
  const canSubmitNameChange = hasPendingNameChange && trimmedNameDraft !== "";
  const variantPolicyByVariant: Record<string, VariantPolicy> = (definition as any).variant_policy ?? {};
  const sameNamePrefabSymbols = definition.type === "prefab" && definition.name
    ? symbols
      .filter(s => s.type === "prefab" && s.name === definition.name)
      .filter(s => !(s.metaPath === activeMeta.path && s.definitionId === defId))
      .sort((a, b) => {
        const av = a.variant || "";
        const bv = b.variant || "";
        return av.localeCompare(bv);
      })
    : [];

  const handleChange = (key: string, value: any) => {
      updateMeta(draft => {
        if (key === 'name' || key === 'displayName' || key === 'description' || key === 'variant_policy') {
              (draft.definitions[defId] as any)[key] = value;
          } else {
              if (value === undefined) {
                  delete draft.definitions[defId].props[key];
              } else {
                  draft.definitions[defId].props[key] = value;
              }
          }
      }, {
          label: key === 'name' || key === 'displayName' || key === 'description' ? `Edit ${key}` : `Edit prop ${key}`,
          mergeKey: `prop:${defId}:${key}`,
      });
  };

  const handleVariantPolicyChange = (variant: string, policy: VariantPolicy) => {
    const nextPolicy: Record<string, VariantPolicy> = {
      ...variantPolicyByVariant,
      [variant]: policy,
    };
    handleChange('variant_policy', nextPolicy);
  };

  const handleEditGeometry = (propKey: string, kind: "rect" | "point" | "image") => {
      setMode({
          kind: "picking",
          definitionId: defId,
          propKey,
          tool: kind
      });
  };

  const handleRenameOnly = () => {
    if (!canSubmitNameChange) {
      return;
    }
    try {
      handleChange("name", trimmedNameDraft);
      setNameDraft(trimmedNameDraft);
    } catch (error: any) {
      setNameDraft(currentName);
      toaster.show({ message: `Rename failed: ${error?.message ?? String(error)}`, intent: "danger" as any });
    }
  };

  const handleRenameWithRefactor = () => {
    if (!canSubmitNameChange) {
      return;
    }
    void (async () => {
      try {
        await executeCommand(
          COMMAND_ID.SYMBOL_RENAME_FOR_DEFINITION,
          commandContext,
          { definitionId: defId, newName: trimmedNameDraft },
        );
        const latestState = useAppStore.getState();
        const latestDocId = latestState.activeDocumentId;
        if (!latestDocId) {
          throw new Error("No active document after symbol rename");
        }
        const latestDoc = latestState.documents[latestDocId];
        if (!latestDoc || !latestDoc.meta) {
          throw new Error("Active document meta is missing after symbol rename");
        }
        const latestDefinition = latestDoc.meta.data.definitions[defId];
        if (!latestDefinition) {
          throw new Error(`Definition not found after symbol rename: ${defId}`);
        }
        setNameDraft(latestDefinition.name || '');
      } catch (error: any) {
        setNameDraft(currentName);
        toaster.show({ message: `Rename failed: ${error?.message ?? String(error)}`, intent: "danger" as any });
      }
    })();
  };

    const renderPropEditor = (key: string, value: PropValue | undefined, schema?: EditorPropSchema) => {
      const kind = schema?.kind || (typeof value === 'object' ? (value as any).kind : typeof value);
      const Editor = getEditorForType(kind);

      if (!Editor) {
          return <div key={key}>Unknown prop type: {kind}</div>;
      }

      return (
          <Editor
              key={key}
              propKey={key}
              value={value}
              schema={schema}
              onChange={(v) => handleChange(key, v)}
              onEditGeometry={(k) => handleEditGeometry(key, k)}
          />
      );
  };

  const renderedProps = new Set<string>();
  const editors: React.ReactNode[] = [];

  // Common fields

  if (definition.type === "prefab" && projectVariants.length > 0) {
    editors.push(
      <FormGroup key="meta-variant" label="变体">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {projectVariants
            .filter((variant) => variant !== definition.variant)
            .map((variant) => {
              const symbol = sameNamePrefabSymbols.find(s => (s.variant || "base") === variant);
              return (
                <div key={variant} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{  minWidth: 80, whiteSpace: 'nowrap', display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                    {symbol ? (
                      <Button
                        small
                        minimal
                        icon="share"
                        onClick={() => void executeCommand(COMMAND_ID.NAVIGATION_JUMP_TO_SYMBOL, commandContext, { symbol })}
                      />
                    ) : null}
                    {variant}
                  </div>
                  <SegmentedControl
                    options={VARIANT_POLICY_OPTIONS}
                    value={variantPolicyByVariant[variant] ?? 'require'}
                    onChange={(value) => handleVariantPolicyChange(variant, value)}
                    small
                  />
                </div>
              );
            })}
        </div>
      </FormGroup>
    );
  }

  editors.push(
      <FormGroup
        key="common-name"
        label={<span style={{ display: "inline-flex", alignItems: "center", gap: 4 }} ><span>{t('rightProperties.nameClassPath')}</span><HelpIcon content={t('rightProperties.nameClassPathHelp')} /></span>}
      >
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <AutoCompleteInput
              value={nameDraft}
              readOnly={isVariantPrefab}
              onChange={(v) => setNameDraft(v)}
              suggestions={nameSuggestions}
              fill
            />
            {hasPendingNameChange ? (
              <>
                <Tooltip content="仅重命名" position="top">
                  <Button
                    small
                    intent="none"
                    icon="edit"
                    disabled={!canSubmitNameChange}
                    aria-label="仅重命名"
                    style={{ width: 28, minWidth: 28 }}
                    onClick={handleRenameOnly}
                  />
                </Tooltip>
                <Tooltip content="重命名+重构" position="top">
                  <Button
                    small
                    intent="primary"
                    icon="wrench"
                    disabled={!canSubmitNameChange}
                    aria-label="重命名+重构"
                    style={{ width: 28, minWidth: 28 }}
                    onClick={handleRenameWithRefactor}
                  />
                </Tooltip>
              </>
            ) : null}
          </div>
      </FormGroup>
  );
  editors.push(
      <FormGroup key="common-display" label={t('rightProperties.displayName')}>
          <InputGroup value={definition.displayName || ''} onChange={e => handleChange('displayName', e.target.value)} />
      </FormGroup>
  );

  // editors.push(
  //   <FormGroup key="meta-type" label="类型">
  //     <InputGroup readOnly value={definition.type + (definition.prefab_id ? ` (${definition.prefab_id})` : '')} />
  //   </FormGroup>
  // );
  // editors.push(
  //   <FormGroup key="meta-id" label="ID">
  //     <InputGroup readOnly value={defId} />
  //   </FormGroup>
  // );

  // Prefab props
  if (definition.type === 'prefab' && definition.prefab_id && prefabSchema) {
      const schema = prefabSchema.prefabs[definition.prefab_id];
      if (schema) {
          Object.entries(schema.props).forEach(([key, propSchema]) => {
              const hasKey = Object.prototype.hasOwnProperty.call(definition.props, key);
              const storedVal = hasKey ? definition.props[key] : undefined;
              editors.push(
                <OverridableField
                  key={`override:${key}`}
                  isSet={hasKey}
                  onSet={() => {
                    if (propSchema.default_value === undefined) {
                      throw new Error(`Property "${key}" has no default_value in schema.`);
                    }
                    handleChange(key, propSchema.default_value);
                  }}
                  onUnset={() => handleChange(key, undefined)}
                >
                  {renderPropEditor(key, storedVal, propSchema)}
                </OverridableField>
              );
              renderedProps.add(key);
          });
      }
  }

  // Remaining props
  Object.entries(definition.props).forEach(([key, val]) => {
      if (!renderedProps.has(key)) {
          editors.push(
            <OverridableField
              key={`override:remaining:${key}`}
              isSet={true}
              onSet={() => {
                throw new Error(`Cannot set unknown property "${key}" without schema.`);
              }}
              onUnset={() => handleChange(key, undefined)}
            >
              {renderPropEditor(key, val)}
            </OverridableField>
          );
      }
  });



  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, paddingBottom: 20 }}>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
          {editors}
      </div>
    </div>
  );
};
