import React, { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAppStore } from './state';
import { getPrefabSchema } from '../api/prefabs';
import { StageView } from './konva/StageView';
import { LeftToolBar } from '../ui/LeftToolBar';
import { RightProperties } from '../ui/RightProperties';
import { TabBar } from '../ui/TabBar';
import { useSymbolIndexStore } from './symbolIndexStore';
import { TopMenuBar } from '../ui/TopMenuBar';
import { ProblemsPanel } from '../ui/ProblemsPanel';
import { HierarchyPanel } from '../ui/HierarchyPanel';
import { ProjectPanel } from '../ui/ProjectPanel';
import { useSettingsStore } from './settings';
import { FocusSpotlightOverlay } from './FocusSpotlightOverlay';
import { COMMAND_ID, executeCommand } from './commands';
import { useShortcut, useShortcutScope } from '../shortcuts/shortcutManager';
import { installHostBridge, isSingleTabMode } from './host/hostBridge';
import { registerHostHandlers } from './host/hostHandlers';
import { installDocumentStateSync } from './host/documentStateSync';
import { useResize } from '../ui/hooks/useResize';
import { useRecentOpenStore } from './recentOpenStore';
import { useProjectInfoStore } from '../app/projectInfoStore';
import { PanelContainer, PanelView } from '../ui/PanelContainer';
import { usePanelStore } from './panelStore';

export const EditorApp: React.FC = () => {
  const { t } = useTranslation();
  // host mode: 当 editor 以嵌入模式在 VSCode 扩展里执行时
  const isHostMode = window.parent !== window;
  // single tab mode: 禁用多标签页功能，将标签页管理托管给 host（如 VSCode 扩展）
  const singleTabMode = isSingleTabMode();
  const { setPrefabSchema, activeDocumentId } = useAppStore();
  const { initialize } = useSymbolIndexStore();
  const setRecentWorkspaceRoot = useRecentOpenStore((state) => state.setWorkspaceRoot);
  const projectResourceRoot = useProjectInfoStore((state) => state.data?.resource_root ?? null);
  const problemsVisible = useSettingsStore((s) => s.problemsVisible);
  const setProblemsVisible = useSettingsStore((s) => s.setProblemsVisible);
  const problemsHeight = useSettingsStore((s) => s.problemsHeight);
  const setProblemsHeight = useSettingsStore((s) => s.setProblemsHeight);
  const rightPanelWidth = useSettingsStore((s) => s.rightPanelWidth);
  const setRightPanelWidth = useSettingsStore((s) => s.setRightPanelWidth);
  const leftPanelWidth = useSettingsStore((s) => s.leftPanelWidth);
  const setLeftPanelWidth = useSettingsStore((s) => s.setLeftPanelWidth);
  const leftTabIds = usePanelStore((s) => s.getTabsForPanel('left'));
  const hasLeftPanel = leftTabIds.length > 0;

  const { handleMouseDown: handleRightPanelResize } = useResize({
    direction: 'horizontal',
    minSize: 200,
    size: rightPanelWidth,
    onSizeChange: setRightPanelWidth,
    enabled: true,
  });

  const { handleMouseDown: handleLeftPanelResize } = useResize({
    direction: 'horizontal',
    minSize: 160,
    size: leftPanelWidth,
    onSizeChange: setLeftPanelWidth,
    enabled: true,
    reverse: true,
  });

  const commandContext = React.useMemo(
    () => ({
      ui: {},
    }),
    [],
  );

  // All available panel views
  const panelViews: Record<string, PanelView> = React.useMemo(
    () => ({
      properties: {
        id: 'properties',
        title: t('tabs.properties'),
        content: <RightProperties />,
      },
      hierarchy: {
        id: 'hierarchy',
        title: t('tabs.hierarchy'),
        content: <HierarchyPanel />,
      },
      project: {
        id: 'project',
        title: t('tabs.project'),
        content: <ProjectPanel />,
      },
    }),
    [t],
  );

  useEffect(() => {
    getPrefabSchema().then(setPrefabSchema).catch(console.error);
  }, [setPrefabSchema]);

  useEffect(() => {
    initialize().catch(console.error);
  }, [initialize]);

  useEffect(() => {
    setRecentWorkspaceRoot(projectResourceRoot);
  }, [projectResourceRoot, setRecentWorkspaceRoot]);

  useEffect(() => {
    const disposeHandlers = registerHostHandlers();
    const uninstall = installHostBridge();
    const uninstallStateSync = isHostMode ? installDocumentStateSync() : () => {};
    return () => {
      uninstallStateSync();
      uninstall();
      disposeHandlers();
    };
  }, [isHostMode]);

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
        {/* Left panel tab container – leftmost */}
        {hasLeftPanel && (
          <div style={{ display: 'flex', background: '#e1e8ed', borderRight: '1px solid #c5d2db' }}>
            <div style={{ width: leftPanelWidth, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
              <PanelContainer panelId="left" views={panelViews} />
            </div>
            <div
              onMouseDown={handleLeftPanelResize}
              style={{ width: 4, cursor: 'col-resize', background: '#d2dce5', flexShrink: 0 }}
              title={t('leftPanel.resizePanel')}
            />
          </div>
        )}

        {/* Tools bar */}
        <div style={{ width: 60, background: '#e1e8ed', borderRight: '1px solid #c5d2db', padding: '10px 5px' }}>
          <LeftToolBar />
        </div>

        <div style={{ flex: 1, background: '#f5f8fa', position: 'relative', display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          {singleTabMode ? null : <TabBar />}
          <div style={{ flex: 1, position: 'relative', minHeight: 0 }}>
            {activeDocumentId ? (
              <StageView />
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#5c7080' }}>
                {t('status.noImageLoaded')}
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

        {/* Right panel */}
        <div style={{ display: 'flex', background: '#e1e8ed', borderLeft: '1px solid #c5d2db' }}>
          <div
            onMouseDown={handleRightPanelResize}
            style={{ width: 4, cursor: 'col-resize', background: '#d2dce5' }}
            title={t('rightPanel.resizePanel')}
          />
          <div style={{ width: rightPanelWidth, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <PanelContainer panelId="right" views={panelViews} />
          </div>
        </div>
      </div>
      <FocusSpotlightOverlay />
    </div>
  );
};
