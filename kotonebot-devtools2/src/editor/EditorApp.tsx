import React, { useEffect, useState } from 'react';
import { useAppStore } from './state';
import { getPrefabSchema } from '../api/prefabs';
import { StageView } from './konva/StageView';
import { LeftToolBar } from '../ui/LeftToolBar';
import { RightProperties } from '../ui/RightProperties';
import { TabBar } from '../ui/TabBar';
import { useSymbolIndexStore } from './symbolIndexStore';
import { useCommandPaletteShortcut } from '../hooks/useCommandPaletteShortcut';
import { CommandPalette } from '../ui/CommandPalette';
import { TopMenuBar } from '../ui/TopMenuBar';
import { ProblemsPanel } from '../ui/ProblemsPanel';
import { useSettingsStore } from './settings';

export const EditorApp: React.FC = () => {
  const { setPrefabSchema, activeDocumentId } = useAppStore();
  const { initialize } = useSymbolIndexStore();
  const [isPaletteOpen, setPaletteOpen] = useState(false);
  const problemsVisible = useSettingsStore((s) => s.problemsVisible);
  const setProblemsVisible = useSettingsStore((s) => s.setProblemsVisible);
  const problemsHeight = useSettingsStore((s) => s.problemsHeight);
  const setProblemsHeight = useSettingsStore((s) => s.setProblemsHeight);

  useEffect(() => {
    getPrefabSchema().then(setPrefabSchema).catch(console.error);
  }, [setPrefabSchema]);

  useEffect(() => {
    initialize().catch(console.error);
  }, [initialize]);

  useCommandPaletteShortcut(() => setPaletteOpen(true));

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const isTyping =
        target instanceof HTMLInputElement ||
        target instanceof HTMLTextAreaElement ||
        target?.isContentEditable;
      if (isTyping) {
        return;
      }
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === "m") {
        e.preventDefault();
        setProblemsVisible(!useSettingsStore.getState().problemsVisible);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [setProblemsVisible]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw', background: '#f5f8fa' }}>
      <TopMenuBar
        onOpenCommandPalette={() => setPaletteOpen(true)}
      />
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
          <ProblemsPanel
            visible={problemsVisible}
            height={problemsHeight}
            onToggleVisible={() => setProblemsVisible(!problemsVisible)}
            onClose={() => setProblemsVisible(false)}
            onHeightChange={setProblemsHeight}
          />
        </div>

        <div style={{ width: 300, background: '#e1e8ed', borderLeft: '1px solid #c5d2db', padding: 10, overflowY: 'auto' }}>
          <h3 style={{ color: '#182026', margin: '0 0 10px 0' }}>Properties</h3>
          <RightProperties />
        </div>
      </div>
      <CommandPalette
        isOpen={isPaletteOpen}
        onClose={() => setPaletteOpen(false)}
      />
    </div>
  );
};
