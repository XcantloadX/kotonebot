import React, { useEffect } from 'react';
import { useAppStore } from './state';
import { getPrefabSchema } from '../api/prefabs';
import { StageView } from './konva/StageView';
import { LeftToolBar } from '../ui/LeftToolBar';
import { RightProperties } from '../ui/RightProperties';
import { TabBar } from '../ui/TabBar';
import { useSymbolIndexStore } from './symbolIndexStore';
import { TopMenuBar } from '../ui/TopMenuBar';
import { ProblemsPanel } from '../ui/ProblemsPanel';
import { useSettingsStore } from './settings';
import { FocusSpotlightOverlay } from './FocusSpotlightOverlay';
import { COMMAND_ID, executeCommand } from './commands';
import { useShortcut, useShortcutScope } from '../shortcuts/shortcutManager';
import { installHostBridge } from './host/hostBridge';
import { registerHostHandlers } from './host/hostHandlers';

export const EditorApp: React.FC = () => {
  // host mode: 当 editor 以嵌入模式在 VSCode 扩展里执行时
  const isHostMode = window.parent !== window;
  const { setPrefabSchema, activeDocumentId } = useAppStore();
  const { initialize } = useSymbolIndexStore();
  const problemsVisible = useSettingsStore((s) => s.problemsVisible);
  const setProblemsVisible = useSettingsStore((s) => s.setProblemsVisible);
  const problemsHeight = useSettingsStore((s) => s.problemsHeight);
  const setProblemsHeight = useSettingsStore((s) => s.setProblemsHeight);
  const commandContext = React.useMemo(
    () => ({
      ui: {},
    }),
    [],
  );

  useEffect(() => {
    getPrefabSchema().then(setPrefabSchema).catch(console.error);
  }, [setPrefabSchema]);

  useEffect(() => {
    initialize().catch(console.error);
  }, [initialize]);

  useEffect(() => {
    const disposeHandlers = registerHostHandlers();
    const uninstall = installHostBridge();
    return () => {
      uninstall();
      disposeHandlers();
    };
  }, []);

  useShortcutScope("editor", true);

  useShortcut({
    id: "editor.open-command-palette",
    scope: "editor",
    combo: "mod+shift+p",
    when: () => !isHostMode,
    onKeyDown: () => {
      void executeCommand(COMMAND_ID.APP_OPEN_COMMAND_PALETTE, commandContext, undefined);
    },
  });

  useShortcut({
    id: "editor.toggle-problems-panel",
    scope: "editor",
    combo: "mod+shift+m",
    onKeyDown: () => {
      void executeCommand(COMMAND_ID.APP_TOGGLE_PROBLEMS_PANEL, commandContext, undefined);
    },
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', background: '#f5f8fa' }}>
      {!isHostMode ? (
        <TopMenuBar />
      ) : null}
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        <div style={{ width: 60, background: '#e1e8ed', borderRight: '1px solid #c5d2db', padding: '10px 5px' }}>
          <LeftToolBar />
        </div>

        <div style={{ flex: 1, background: '#f5f8fa', position: 'relative', display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <TabBar />
          <div style={{ flex: 1, position: 'relative', minHeight: 0 }}>
            {activeDocumentId ? (
              <StageView />
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#5c7080' }}>
                No image loaded
              </div>
            )}
          </div>
          {!isHostMode ? (
            <ProblemsPanel
              visible={problemsVisible}
              height={problemsHeight}
              onToggleVisible={() => setProblemsVisible(!problemsVisible)}
              onClose={() => setProblemsVisible(false)}
              onHeightChange={setProblemsHeight}
            />
          ) : null}
        </div>

        <div style={{ width: 300, background: '#e1e8ed', borderLeft: '1px solid #c5d2db', padding: 10, overflowY: 'auto' }}>
          <h3 style={{ color: '#182026', margin: '0 0 10px 0' }}>Properties</h3>
          <RightProperties />
        </div>
      </div>
      <FocusSpotlightOverlay />
    </div>
  );
};
