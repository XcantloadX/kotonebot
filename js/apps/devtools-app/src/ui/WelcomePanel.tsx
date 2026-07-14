import React from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@blueprintjs/core';
import { useRecentOpenStore } from '../editor/recentOpenStore';
import { COMMAND_ID, executeCommand } from '../editor/commands';
import { editorActions } from '../editor/actions';
import { useEditorDialogsContext } from '../editor/EditorDialogsContext';

const MAX_RECENT_ITEMS = 12;

export const WelcomePanel: React.FC = () => {
  const { t } = useTranslation();
  const { commandContext } = useEditorDialogsContext();
  const recentItems = useRecentOpenStore((state) => {
    const items = state.itemsByWorkspace[state.currentWorkspaceKey] ?? [];
    return items.slice(0, MAX_RECENT_ITEMS);
  });

  const handleOpenRecent = async (imagePath: string) => {
    await editorActions.image.openWithMeta(imagePath, { allowHostDelegate: true, source: "other" });
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        userSelect: 'none',
      }}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, minWidth: 280 }}>
        <div style={{ fontSize: 20, fontWeight: 600, color: '#182026' }}>
          {t('welcome.title')}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}>
          <Button
            minimal
            icon="document"
            onClick={() => void executeCommand(COMMAND_ID.FILE_NEW_DOCUMENT, commandContext, undefined)}
            text={t('welcome.newDocument')}
          />
          <Button
            minimal
            icon="folder-open"
            onClick={() => void executeCommand(COMMAND_ID.FILE_OPEN_IMAGE, commandContext, undefined)}
            text={t('welcome.openDocument')}
          />
        </div>

        {recentItems.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
            <div style={{ fontSize: 20, fontWeight: 600, color: '#182026' }}>
              {t('welcome.recent')}
            </div>
            {recentItems.map((item) => (
              <div
                key={item.imagePath}
                style={{
                  color: '#106ba3',
                  cursor: 'pointer',
                  fontSize: 14,
                  maxWidth: 400,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
                onClick={() => void handleOpenRecent(item.imagePath)}
              >
                {item.imagePath}
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
};
