import React from 'react';
import { FormGroup, InputGroup, Button, H5, Card } from '@blueprintjs/core';
import { useAppStore } from '../editor/state';
import { PropValue } from '../model/metaV2';
import { EditorPropSchema } from '../model/prefabSchema';
import { jumpToSymbol } from '../editor/actions/navigation';
import { promptAndRenameVariantsForDefinition } from '../editor/actions/variantRename';
import { useSymbolIndexStore } from '../editor/symbolIndexStore';
import { getEditorForType } from './properties/PropertyEditorRegistry';
import { OverridableField } from './components/OverridableField';
import { SegmentedControl, SegmentedOption } from './components/SegmentedControl';

type VariantInheritValue = boolean | null;

const VARIANT_INHERIT_OPTIONS: readonly SegmentedOption<VariantInheritValue>[] = [
  { label: 'None', value: null },
  { label: 'False', value: false },
  { label: 'True', value: true },
];

export const RightProperties: React.FC = () => {
  const { activeDocumentId, documents, prefabSchema, updateMeta, setMode } = useAppStore();
  const symbols = useSymbolIndexStore(s => s.symbols);
  const nameValueOnFocusRef = React.useRef<string>('');

  const activeDoc = activeDocumentId ? documents[activeDocumentId] : null;
  const activeMeta = activeDoc?.meta;
  const selection = activeDoc?.selection;

  if (!activeMeta || !selection) {
    return <div style={{ padding: 10, color: '#8a9ba8' }}>No selection</div>;
  }

  const defId = selection.definitionId;
  const definition = activeMeta.data.definitions[defId];

  if (!definition) {
      return <div style={{ padding: 10, color: '#8a9ba8' }}>Definition not found</div>;
  }

  const isVariantPrefab = definition.type === "prefab" && !!definition.variant;
  const variantInheritValue: VariantInheritValue = definition.variant_inherit === true
    ? true
    : definition.variant_inherit === false
      ? false
      : null;
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
          if (key === 'name' || key === 'displayName' || key === 'description' || key === 'variant_inherit') {
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

  const handleEditGeometry = (propKey: string, kind: "rect" | "point" | "image") => {
      setMode({
          kind: "picking",
          definitionId: defId,
          propKey,
          tool: kind
      });
  };

  const handleNameFocus = () => {
    nameValueOnFocusRef.current = definition.name || '';
  };

  const handleNameBlur = () => {
    if (isVariantPrefab) {
      return;
    }
    const valueOnFocus = nameValueOnFocusRef.current;
    const currentValue = definition.name || '';
    if (valueOnFocus === currentValue) {
      return;
    }
    void promptAndRenameVariantsForDefinition(defId);
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
  editors.push(
      <FormGroup key="common-name" label="Name (Class Path)">
          <InputGroup
            value={definition.name || ''}
            readOnly={isVariantPrefab}
            onFocus={handleNameFocus}
            onBlur={handleNameBlur}
            onChange={e => handleChange('name', e.target.value)}
          />
      </FormGroup>
  );
  editors.push(
      <FormGroup key="common-display" label="Display Name">
          <InputGroup value={definition.displayName || ''} onChange={e => handleChange('displayName', e.target.value)} />
      </FormGroup>
  );

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
      <Card compact>
          <H5>{definition.type} {definition.prefab_id ? `(${definition.prefab_id})` : ''}</H5>
          <div style={{ fontSize: 12, color: '#8a9ba8', wordBreak: 'break-all' }}>ID: {defId}</div>
          {definition.type === "prefab" ? (
            <>
              <div style={{ marginTop: 4, fontSize: 12, color: '#5c7080' }}>
                当前 Variant: {definition.variant || "base"}
              </div>
              {!definition.variant ? (
                <div style={{ marginTop: 6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{  color: '#5c7080', whiteSpace: 'nowrap' }}>
                      Variant Inherit
                    </div>
                    <SegmentedControl
                      options={VARIANT_INHERIT_OPTIONS}
                      value={variantInheritValue}
                      onChange={(value) => handleChange('variant_inherit', value)}
                      small
                    />
                  </div>
                </div>
              ) : null}
            </>
          ) : null}
          {sameNamePrefabSymbols.length > 0 ? (
            <div style={{ marginTop: 8, display: "flex", flexWrap: "wrap", gap: 6 }}>
              {sameNamePrefabSymbols.map((symbol) => (
                <Button
                  key={symbol.symbolKey}
                  small
                  minimal
                  icon="share"
                  text={symbol.variant || "base"}
                  onClick={() => void jumpToSymbol(symbol)}
                />
              ))}
            </div>
          ) : null}
          <Button 
            icon="trash" 
            intent="danger" 
            minimal 
            small 
            style={{ position: 'absolute', top: 5, right: 5 }} 
            onClick={() => {
                updateMeta(draft => {
                    delete draft.definitions[defId];
                }, { label: "Delete definition", mergeKey: `delete:${defId}`, forceNewEntry: true });
                setMode({ kind: 'idle' });
            }}
          />
      </Card>
      
      <div style={{ display: 'flex', flexDirection: 'column' }}>
          {editors}
      </div>
    </div>
  );
};
