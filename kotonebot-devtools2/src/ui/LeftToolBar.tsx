import React, { useState, useEffect } from 'react';
import { toaster } from './toaster';
import { useAppStore } from '../editor/state';
import { FileOpenDialog } from './FileOpenDialog';
import { getProjectInfo, readText } from '../api/fs';
import { cloneVariantToImage } from '../api/metaIndex';
import { SideToolBar, Tool } from './SideToolBar';


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
    saveActiveDocument,
    prefabSchema,
    setMode
  } = useAppStore();
  
  const activeDoc = activeDocumentId ? documents[activeDocumentId] : null;
  const activeMeta = activeDoc?.meta;
  const activeMode = activeDoc?.mode;

  const [isImageOpen, setIsImageOpen] = useState(false);
  const [isVariantImageOpen, setIsVariantImageOpen] = useState(false);
  const [pendingVariant, setPendingVariant] = useState<string | null>(null);
  const [projectVariants, setProjectVariants] = useState<string[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const info = await getProjectInfo();
        setProjectVariants(info.resource_variants || []);
      } catch {
        setProjectVariants([]);
      }
    })();
  }, []);

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
    if (activeMode && activeMode.kind === 'creating-prefab') return `prefab-${activeMode.prefab_id}`;
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
      await saveActiveDocument();
      toaster.show({ message: "Saved", intent: "success" });
    } catch (e) {
      toaster.show({ message: "Failed to save", intent: "danger" });
    }
  };

  const openImageWithMeta = async (path: string) => {
    const img = new Image();
    img.src = `/api/image?path=${encodeURIComponent(path)}`;
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = () => reject(new Error(`Failed to load image: ${path}`));
    });
    openDocument(path, img.width, img.height);
    const metaPath = path + ".json";
    const content = await readText(metaPath);
    const data = JSON.parse(content);
    if (data.version !== 2) {
      throw new Error(`Unsupported meta version: ${data.version}`);
    }
    setActiveMeta(path, data);
  };

  const handleCreateVariantDoc = () => {
      if (!activeDoc?.meta) return;
      if (projectVariants.length === 0) {
          toaster.show({ message: "resource_variants 未配置", intent: "warning" });
          return;
      }
      const input = window.prompt(`选择 variant:\n${projectVariants.join(", ")}`, projectVariants[0]);
      if (!input) return;
      const variant = input.trim();
      if (!projectVariants.includes(variant)) {
          toaster.show({ message: `非法 variant: ${variant}`, intent: "danger" });
          return;
      }
      setPendingVariant(variant);
      setIsVariantImageOpen(true);
  };

  const handleVariantImageSelect = async (paths: string[]) => {
      if (!activeDoc?.meta || !pendingVariant) return;
      if (paths.length !== 1) {
          throw new Error("Variant image clone requires single target image");
      }
      const targetImagePath = paths[0];
      try {
          await cloneVariantToImage({
              sourceMetaPath: activeDoc.meta.path,
              targetImagePath,
              variant: pendingVariant,
              forceOverwrite: false,
          });
      } catch (e: any) {
          const message = e?.message ?? String(e);
          if (message.includes("Target meta already exists")) {
              const confirmed = window.confirm("目标 meta 已存在，确认覆盖全部 definitions（不会保留原数据）？");
              if (!confirmed) {
                  setIsVariantImageOpen(false);
                  setPendingVariant(null);
                  return;
              }
              await cloneVariantToImage({
                  sourceMetaPath: activeDoc.meta.path,
                  targetImagePath,
                  variant: pendingVariant,
                  forceOverwrite: true,
              });
          } else {
              throw e;
          }
      }
      await openImageWithMeta(targetImagePath);
      toaster.show({ message: `已创建 ${pendingVariant} variant 文档`, intent: "success" });
      setIsVariantImageOpen(false);
      setPendingVariant(null);
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
          id: 'clone-variant-doc',
          icon: 'duplicate',
          title: '新建 Variant 图片文档',
          onClick: handleCreateVariantDoc,
          selectable: false,
          disabled: !activeDoc?.meta
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
        filter={name => name.endsWith('.png')}
      />
      <FileOpenDialog
        isOpen={isVariantImageOpen}
        onClose={() => {
          setIsVariantImageOpen(false);
          setPendingVariant(null);
        }}
        onSelect={handleVariantImageSelect}
        title={`选择 ${pendingVariant || ""} Variant 目标图片`}
        filter={name => name.endsWith('.png')}
        multiSelect={false}
      />
    </>
  );
};
