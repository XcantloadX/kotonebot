import React, { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAppStore } from './state';
import { selectActiveTab } from './commands/selectors';
import { getPrefabSchema } from '../api/prefabs';
import { StageView } from './konva/StageView';
import { LeftToolBar } from '../ui/LeftToolBar';
import { RightProperties } from '../ui/RightProperties';
import { TabBar } from '../ui/TabBar';
import { useSymbolIndexStore } from './symbolIndexStore';
import { TopMenuBar } from '../ui/TopMenuBar';
import { ProblemsPanel } from '../ui/ProblemsPanel';
import { WelcomePanel } from '../ui/WelcomePanel';
import { HierarchyPanel } from '../ui/HierarchyPanel';
import { ProjectPanel } from '../ui/ProjectPanel';
import { useSettingsStore } from './settings';
import { FocusSpotlightOverlay } from './FocusSpotlightOverlay';
import { useShortcutScope } from '../shortcuts/shortcutManager';
import { EditorDialogsProvider } from './EditorDialogsContext';
import { EditorShortcuts } from './EditorShortcuts';
import { installHostBridge, isSingleTabMode } from './host/hostBridge';
import { registerHostHandlers } from './host/hostHandlers';
import { installDocumentStateSync } from './host/documentStateSync';
import { Tabs, Tab } from '@blueprintjs/core';
import { useResize } from '../ui/hooks/useResize';
import { useRecentOpenStore } from './recentOpenStore';
import { useProjectInfoStore } from '../app/projectInfoStore';

export const EditorApp: React.FC = () => {
  const { t } = useTranslation();
  const isHostMode = window.parent !== window;
  const singleTabMode = isSingleTabMode();
  const { setPrefabSchema } = useAppStore();
  const activeTab = useAppStore(selectActiveTab);
  const { initialize } = useSymbolIndexStore();
  const setRecentWorkspaceRoot = useRecentOpenStore((state) => state.setWorkspaceRoot);
  const projectResourceRoot = useProjectInfoStore((state) => state.data?.resource_root ?? null);
  const problemsVisible = useSettingsStore((s) => s.problemsVisible);
  const setProblemsVisible = useSettingsStore((s) => s.setProblemsVisible);
  const problemsHeight = useSettingsStore((s) => s.problemsHeight);
  const setProblemsHeight = useSettingsStore((s) => s.setProblemsHeight);
  const rightPanelWidth = useSettingsStore((s) => s.rightPanelWidth);
  const setRightPanelWidth = useSettingsStore((s) => s.setRightPanelWidth);
  const { handleMouseDown: handleRightPanelResize } = useResize({
    direction: 'horizontal',
    minSize: 200,
    size: rightPanelWidth,
    onSizeChange: setRightPanelWidth,
    enabled: true,
  });

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

  return (
    <EditorDialogsProvider>
      <EditorShortcuts />
      <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', background: '#f5f8fa' }}>
        {!isHostMode ? (
          <TopMenuBar />
        ) : null}
        <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
          <div style={{ width: 60, background: '#e1e8ed', borderRight: '1px solid #c5d2db', padding: '10px 5px' }}>
            <LeftToolBar />
          </div>

          <div style={{ flex: 1, background: '#f5f8fa', position: 'relative', display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            {singleTabMode ? null : <TabBar />}
            <div style={{ flex: 1, position: 'relative', minHeight: 0 }}>
              {activeTab?.kind === "document" ? <StageView /> : <WelcomePanel />}
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

          <div style={{ display: 'flex', background: '#e1e8ed', borderLeft: '1px solid #c5d2db' }}>
            <div
              onMouseDown={handleRightPanelResize}
              style={{ width: 4, cursor: 'col-resize', background: '#d2dce5' }}
              title={t('rightPanel.resizePanel')}
            />
            <div style={{ width: rightPanelWidth, display: 'flex', flexDirection: 'column', padding: '0 10px', minHeight: 0 }}>
              <Tabs id="right-panel-tabs" className="kb-right-tabs" defaultSelectedTabId="properties">
                <Tab id="properties" title={t('tabs.properties')} panelClassName="kb-right-tabs-panel" panel={<RightProperties />} />
                <Tab id="hierarchy" title={t('tabs.hierarchy')} panelClassName="kb-right-tabs-panel" panel={<HierarchyPanel />} />
                <Tab id="project" title={t('tabs.project')} panelClassName="kb-right-tabs-panel" panel={<ProjectPanel />} />
              </Tabs>
            </div>
          </div>
        </div>
        <FocusSpotlightOverlay />
      </div>
    </EditorDialogsProvider>
  );
};
