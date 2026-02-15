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

export const EditorApp: React.FC = () => {
  const {
    setPrefabSchema,
    activeDocumentId,
  } = useAppStore();
  const { initialize } = useSymbolIndexStore();
  const [isPaletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    getPrefabSchema().then(setPrefabSchema).catch(console.error);
  }, []);

  useEffect(() => {
    initialize().catch(console.error);
  }, [initialize]);

  useCommandPaletteShortcut(() => setPaletteOpen(true));

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', background: '#f5f8fa' }}>
      <div style={{ width: 60, background: '#e1e8ed', borderRight: '1px solid #c5d2db', padding: '10px 5px' }}>
        <LeftToolBar />
      </div>
      
      <div style={{ flex: 1, background: '#f5f8fa', position: 'relative', display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <TabBar />
        <div style={{ flex: 1, position: 'relative' }}>
            {activeDocumentId ? (
              <StageView />
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#5c7080' }}>
                No image loaded
              </div>
            )}
        </div>
      </div>
      
      <div style={{ width: 300, background: '#e1e8ed', borderLeft: '1px solid #c5d2db', padding: 10, overflowY: 'auto' }}>
        <h3 style={{ color: '#182026', margin: '0 0 10px 0' }}>Properties</h3>
        <RightProperties />
      </div>
      <CommandPalette
        isOpen={isPaletteOpen}
        onClose={() => setPaletteOpen(false)}
      />
    </div>
  );
};
