import React, { useState, useEffect } from 'react';
import { Toaster, Position as ToasterPosition } from '@blueprintjs/core';
import { useAppStore } from '../editor/state';
import { FileOpenDialog } from './FileOpenDialog';
import { readText, writeText } from '../api/fs';
import { SideToolBar, Tool } from './SideToolBar';

const toaster = Toaster.create({ position: ToasterPosition.TOP });

export const LeftToolBar: React.FC = () => {
  const { 
    activeDocumentId,
    documents,
    openDocument,
    setActiveMeta, 
    activeTool,
    setActiveTool,
    activeResourceType,
    setActiveResourceType,
    undo,
    redo,
    markAsSaved,
    prefabSchema,
    setMode,
    mode
  } = useAppStore();
  
  const activeDoc = activeDocumentId ? documents[activeDocumentId] : null;
  const activeMeta = activeDoc?.meta;

  const [isImageOpen, setIsImageOpen] = useState(false);

  useEffect(() => {
      const handleKeyDown = (e: KeyboardEvent) => {
          if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
              return;
          }

          if (e.ctrlKey && e.key === 'o') {
              e.preventDefault();
              setIsImageOpen(true);
          } else if (e.ctrlKey && e.key === 's') {
              e.preventDefault();
              handleSave();
          } else if (e.ctrlKey && e.shiftKey && (e.key === 'z' || e.key === 'Z')) {
              e.preventDefault();
              redo();
          } else if (e.ctrlKey && e.key === 'z') {
              e.preventDefault();
              undo();
          } else if (e.key === 'v') {
              setActiveTool('select');
          } else if (prefabSchema) {
              const key = e.key.toLowerCase();
              const isCtrl = e.ctrlKey;
              const target = Object.values(prefabSchema.prefabs).find(p => {
                  if (!p.shortcut) return false;
                  const s = p.shortcut.toLowerCase();
                  if (s.startsWith('ctrl+')) {
                      return isCtrl && s.slice(5) === key;
                  }
                  return !isCtrl && s === key;
              });
              if (target) {
                  e.preventDefault();
                  createPrefab(target.id);
              }
          }
      };

      window.addEventListener('keydown', handleKeyDown);
      return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeMeta, undo, redo, setActiveTool, prefabSchema]);

  const getSelectedToolId = () => {
    if (mode && mode.kind === 'creating-prefab') return `prefab-${mode.prefab_id}`;
    if (activeTool === 'select') return 'select';
    if (activeTool === 'rect') {
        if (activeResourceType === 'template') return 'new-template';
        if (activeResourceType === 'hint-box') return 'new-hint-box';
    }
    if (activeTool === 'point') {
        if (activeResourceType === 'hint-point') return 'new-hint-point';
    }
    return undefined;
  };

  const handleSelect = async (paths: string[]) => {
    for (const path of paths) {
        const img = new Image();
        img.src = `/api/image?path=${encodeURIComponent(path)}`;
        await new Promise((resolve, reject) => {
            img.onload = resolve;
            img.onerror = reject;
        });
        
        openDocument(path, img.width, img.height);
        
        // Try load meta
        const metaPath = path + ".json";
        try {
            const content = await readText(metaPath);
            const data = JSON.parse(content);
            if (data.version === 2) {
                setActiveMeta(path, data);
            } else {
                console.warn("Legacy meta or unknown format, starting fresh V2");
                setActiveMeta(path, { version: 2, definitions: {} });
            }
        } catch (e) {
            setActiveMeta(path, { version: 2, definitions: {} });
        }
    }
    setIsImageOpen(false);
  };

  const handleSave = async () => {
    if (!activeMeta || !activeDoc) return;
    try {
      await writeText(activeMeta.path, JSON.stringify(activeMeta.data, null, 2));
      toaster.show({ message: "Saved", intent: "success" });
      markAsSaved();
    } catch (e) {
      toaster.show({ message: "Failed to save", intent: "danger" });
    }
  };

  const createPrefab = (prefabId: string) => {
      if (!activeMeta || !prefabSchema) return;
      
      const schema = prefabSchema.prefabs[prefabId];

      if (schema.primary_prop) {
          const primaryPropSchema = schema.props[schema.primary_prop];
          if (primaryPropSchema) {
              setMode({
                  kind: "creating-prefab",
                  prefab_id: prefabId,
                  propKey: schema.primary_prop,
                  tool: primaryPropSchema.kind as any
              });
              return;
          }
      }
      
      toaster.show({ message: `No primary prop defined for prefab '${schema.name}'`, intent: "danger" });
  };

  const tools: Array<Tool | 'separator'> = [
      {
          id: 'open',
          icon: 'document',
          title: '打开',
          onClick: () => setIsImageOpen(true),
          selectable: false
      },
      {
          id: 'save',
          icon: 'floppy-disk',
          title: '保存',
          onClick: handleSave,
          selectable: false,
          disabled: !activeMeta
      },
      'separator',
      {
          id: 'undo',
          icon: 'undo',
          title: '撤销',
          selectable: false,
          onClick: () => undo()
      },
      {
          id: 'redo',
          icon: 'redo',
          title: '重做',
          selectable: false,
          onClick: () => redo()
      },
      'separator',
      {
          id: 'select',
          icon: 'select',
          title: '选择',
          selectable: true,
          onClick: () => setActiveTool('select')
      },
      'separator',
  ];

  let _prefabAdded = false;
  if (prefabSchema) {
      Object.values(prefabSchema.prefabs).forEach(p => {
          tools.push({
              id: `prefab-${p.id}`,
              icon: p.icon as any,
              title: `${p.name} (${p.shortcut || 'no shortcut'})`,
              selectable: true,
              onClick: () => createPrefab(p.id),
              disabled: !activeMeta
          });
          _prefabAdded = true;
      });
  }

  if (_prefabAdded) {
      tools.push('separator');
  }

  tools.push({
      id: 'new-template',
      icon: 'media',
      title: '简单模板',
      selectable: true,
      onClick: () => {
          setActiveResourceType('template');
          setActiveTool('rect');
      },
      disabled: !activeMeta
  });
  tools.push({
      id: 'new-hint-box',
      icon: 'selection',
      title: '简单 Hint Box',
      selectable: true,
      onClick: () => {
          setActiveResourceType('hint-box');
          setActiveTool('rect');
      },
      disabled: !activeMeta
  });
  tools.push({
      id: 'new-hint-point',
      icon: 'locate',
      title: '简单 Hint Point',
      selectable: true,
      onClick: () => {
          setActiveResourceType('hint-point');
          setActiveTool('point');
      },
      disabled: !activeMeta
  });

  return (
    <>
      <SideToolBar tools={tools} selectedToolId={getSelectedToolId()} />
      <FileOpenDialog 
        isOpen={isImageOpen} 
        onClose={() => setIsImageOpen(false)} 
        onSelect={handleSelect}
        title="Open Image"
        filter={name => name.endsWith('.png') || name.endsWith('.jpg')}
      />
    </>
  );
};
