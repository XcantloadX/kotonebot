import React from 'react';
import { FormGroup, InputGroup, Button, H5, Card } from '@blueprintjs/core';
import { useAppStore } from '../editor/state';
import { PropValue } from '../model/metaV2';
import { EditorPropSchema } from '../model/prefabSchema';
import { jumpToSymbol } from '../editor/actions/navigation';
import { useSymbolIndexStore } from '../editor/symbolIndexStore';
import { getEditorForType } from './properties/PropertyEditorRegistry';

export const RightProperties: React.FC = () => {
  const { activeDocumentId, documents, prefabSchema, updateMeta, setMode } = useAppStore();
  const symbols = useSymbolIndexStore(s => s.symbols);

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
          if (key === 'name' || key === 'displayName' || key === 'description') {
              (draft.definitions[defId] as any)[key] = value;
          } else {
              if (value === undefined) {
                  delete draft.definitions[defId].props[key];
              } else {
                  draft.definitions[defId].props[key] = value;
              }
          }
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
              editors.push(renderPropEditor(key, storedVal, propSchema));
              renderedProps.add(key);
          });
      }
  }

  // Remaining props
  Object.entries(definition.props).forEach(([key, val]) => {
      if (!renderedProps.has(key)) {
          editors.push(renderPropEditor(key, val));
      }
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, paddingBottom: 20 }}>
      <Card compact>
          <H5>{definition.type} {definition.prefab_id ? `(${definition.prefab_id})` : ''}</H5>
          <div style={{ fontSize: 12, color: '#8a9ba8', wordBreak: 'break-all' }}>ID: {defId}</div>
          {definition.type === "prefab" ? (
            <div style={{ marginTop: 4, fontSize: 12, color: '#5c7080' }}>
              当前 Variant: {definition.variant || "base"}
            </div>
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
                });
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
