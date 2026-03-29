import React, { useMemo, useRef, useState, useEffect, useCallback } from 'react';
import { Icon, Menu, MenuItem } from '@blueprintjs/core';
import { useTranslation } from 'react-i18next';
import { useAppStore } from '../editor/state';
import { useSymbolIndexStore } from '../editor/symbolIndexStore';
import { COMMAND_ID, executeCommand } from '../editor/commands';
import { editorActions } from '../editor/actions';
import { DefinitionModel } from '../model/metaV2';

function getTypeIcon(def: DefinitionModel, prefabSchema: ReturnType<typeof useAppStore.getState>['prefabSchema']): string {
  if (def.type === 'prefab' && def.prefab_id && prefabSchema) {
    const schema = prefabSchema.prefabs[def.prefab_id];
    if (schema?.icon) return schema.icon;
  }
  switch (def.type) {
    case 'template': return 'media';
    case 'hint-box': return 'selection';
    case 'hint-point': return 'locate';
    default: return 'cube';
  }
}

export const HierarchyPanel: React.FC = () => {
  const { t } = useTranslation();
  const activeDocumentId = useAppStore((s) => s.activeDocumentId);
  const documents = useAppStore((s) => s.documents);
  const setSelection = useAppStore((s) => s.setSelection);
  const prefabSchema = useAppStore((s) => s.prefabSchema);
  const symbols = useSymbolIndexStore((s) => s.symbols);

  const activeDoc = activeDocumentId ? documents[activeDocumentId] : null;
  const activeMeta = activeDoc?.meta;
  const selection = activeDoc?.selection;

  const commandContext = useMemo(() => ({ ui: {} }), []);
  const contextMenuRef = useRef<HTMLDivElement>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; definitionId: string } | null>(null);

  const definitions = useMemo(() => {
    if (!activeMeta) return [];
    return Object.entries(activeMeta.data.definitions).map(([id, def]) => ({
      id,
      def,
    }));
  }, [activeMeta]);

  useEffect(() => {
    if (!contextMenu) return;
    const closeOnPointerDown = (e: MouseEvent) => {
      const target = e.target as Node;
      const isInMenu = contextMenuRef.current?.contains(target) ?? false;
      if (!isInMenu) {
        setContextMenu(null);
      }
    };
    window.addEventListener('mousedown', closeOnPointerDown);
    return () => window.removeEventListener('mousedown', closeOnPointerDown);
  }, [contextMenu]);

  useEffect(() => {
    setContextMenu(null);
  }, [activeDocumentId]);

  const handleContextMenu = (e: React.MouseEvent, definitionId: string) => {
    e.preventDefault();
    e.stopPropagation();
    setSelection(definitionId);
    setContextMenu({ x: e.clientX, y: e.clientY, definitionId });
  };

  const contextDef = useMemo(() => {
    if (!contextMenu || !activeMeta) return null;
    return activeMeta.data.definitions[contextMenu.definitionId] ?? null;
  }, [contextMenu, activeMeta]);

  const canCopySelectedPrefabToVariant = !!contextDef && contextDef.type === 'prefab';

  const closeContextMenu = useCallback(() => setContextMenu(null), []);

  if (!activeDocumentId) {
    return (
      <div style={{ padding: 16, color: '#5c7080', fontSize: 13, textAlign: 'center' }}>
        {t('status.noActiveDocument')}
      </div>
    );
  }

  if (definitions.length === 0) {
    return (
      <div style={{ padding: 16, color: '#5c7080', fontSize: 13, textAlign: 'center' }}>
        {t('status.noObjects')}
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflow: 'auto', background: '#f5f8fa' }}>
      {definitions.map(({ id, def }) => {
        const isSelected = selection?.definitionId === id;
        const icon = getTypeIcon(def, prefabSchema);
        const name = def.name || id.slice(0, 8);
        const hasDisplayName = !!def.displayName && def.displayName !== def.name;

        return (
          <button
            key={id}
            type="button"
            onClick={() => {
              const symbol = symbols.find(
                (s) => s.definitionId === id && s.imagePath === activeDocumentId
              );
              if (symbol) {
                void editorActions.navigation.jumpToSymbol(symbol);
              } else {
                setSelection(id);
              }
            }}
            onContextMenu={(e) => handleContextMenu(e, id)}
            style={{
              width: '100%',
              textAlign: 'left',
              border: 'none',
              borderLeft: isSelected ? '3px solid #106ba3' : '3px solid transparent',
              borderBottom: '1px solid #e1e8ed',
              background: isSelected ? '#e6eff6' : 'transparent',
              padding: '6px 10px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <Icon icon={icon as any} style={{ color: '#5c7080', flexShrink: 0 }} />
            <span style={{ fontSize: 13, color: '#182026', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {name}
            </span>
            {hasDisplayName && (
              <span style={{ fontSize: 11, color: '#a0aab4', marginLeft: 8, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {def.displayName}
              </span>
            )}
          </button>
        );
      })}

      {contextMenu ? (
        <div
          ref={contextMenuRef}
          style={{
            position: 'fixed',
            left: contextMenu.x,
            top: contextMenu.y,
            zIndex: 2600,
            minWidth: 180,
            background: '#ffffff',
            border: '1px solid #b7c6d2',
            borderRadius: 3,
            boxShadow: '0 6px 18px rgba(16, 22, 26, 0.22)',
          }}
          onMouseDown={(e) => e.stopPropagation()}
          onContextMenu={(e) => e.preventDefault()}
        >
          <Menu>
            <MenuItem
              icon="duplicate"
              text={t('contextMenu.duplicate')}
              onClick={() => {
                void executeCommand(COMMAND_ID.DEFINITION_DUPLICATE_SELECTED, commandContext, undefined);
                closeContextMenu();
              }}
            />
            <MenuItem
              icon="duplicate"
              text={t('contextMenu.copy')}
              onClick={() => {
                void executeCommand(COMMAND_ID.DEFINITION_COPY_SELECTED, commandContext, undefined);
                closeContextMenu();
              }}
            />
            <MenuItem
              icon="cut"
              text={t('contextMenu.cut')}
              onClick={() => {
                void executeCommand(COMMAND_ID.DEFINITION_CUT_SELECTED, commandContext, undefined);
                closeContextMenu();
              }}
            />
            <MenuItem
              icon="trash"
              text={t('contextMenu.delete')}
              intent="danger"
              onClick={() => {
                void executeCommand(COMMAND_ID.DEFINITION_DELETE_SELECTED, commandContext, undefined);
                closeContextMenu();
              }}
            />
            <MenuItem
              icon="duplicate"
              text={t('contextMenu.copyToVariant')}
              disabled={!canCopySelectedPrefabToVariant}
              onClick={() => {
                void executeCommand(COMMAND_ID.VARIANT_COPY_SELECTED_PREFAB, commandContext, undefined);
                closeContextMenu();
              }}
            />
          </Menu>
        </div>
      ) : null}
    </div>
  );
};
