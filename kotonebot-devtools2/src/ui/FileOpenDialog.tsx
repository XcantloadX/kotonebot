import React, { useState, useEffect, useRef } from 'react';
import { Dialog, Classes, Button, ButtonGroup, Tree, TreeNodeInfo, Spinner, Popover, PopoverInteractionKind, Position, InputGroup } from '@blueprintjs/core';
import ClearableInputGroup from '@/ui/components/ClearableInputGroup';
import { toaster } from '../ui/toaster';
import { listDir, getProjectInfo, FileItem, getImageUrl } from '../api/fs';
import { useSettingsStore } from "../editor/settings";

interface FileOpenDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (paths: string[]) => void;
  title?: string;
  filter?: (name: string) => boolean;
}

interface ThumbnailGridProps {
  items: FileItem[];
  selectedPaths: Set<string>;
  thumbSize: number;
  onOpenDirectory: (path: string) => void;
  onToggleSelect: (path: string, ctrlKey: boolean, shiftKey: boolean) => void;
}

const ThumbnailGrid: React.FC<ThumbnailGridProps> = ({
  items,
  selectedPaths,
  thumbSize,
  onOpenDirectory,
  onToggleSelect,
}) => {
  return (
    <div
      style={{
        padding: 8,
        display: "grid",
        gridTemplateColumns: `repeat(auto-fill, minmax(${thumbSize}px, 1fr))`,
        gap: 8,
      }}
    >
      {items.map((item) => {
          const normalizedPath = item.path.replace(/\\/g, "/");
          const isSelected = selectedPaths.has(normalizedPath);
          const isImage = !!item.isImage;
          const thumbnailUrl = item.thumbnailUrl || (isImage ? getImageUrl(normalizedPath) : undefined);
          const iconSize = Math.max(16, Math.floor(thumbSize / 3));

          return (
            <div
              key={normalizedPath}
              onClick={(e) => {
                const ctrlKey = e.ctrlKey || e.metaKey;
                const shiftKey = e.shiftKey;
                if (item.isDirectory) {
                  onOpenDirectory(item.path);
                } else {
                  onToggleSelect(normalizedPath, ctrlKey, shiftKey);
                }
              }}
              style={{
                border: isSelected ? "2px solid #137cbd" : "1px solid #d1d8e0",
                borderRadius: 4,
                padding: 4,
                cursor: "pointer",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "flex-start",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: thumbSize - 8,
                  height: thumbSize - 8,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: "#f5f8fa",
                  overflow: "hidden",
                }}
              >
                {isImage && thumbnailUrl ? (
                  <img
                    src={thumbnailUrl}
                    alt={item.name}
                    style={{ width: "100%", height: "100%", objectFit: "contain" }}
                  />
                ) : (
                  <span
                    className={item.isDirectory ? "bp5-icon bp5-icon-folder-close" : "bp5-icon bp5-icon-document"}
                    style={{ fontSize: iconSize }}
                  />
                )}
              </div>
              <div
                style={{
                  marginTop: 4,
                  fontSize: 12,
                  textAlign: "center",
                  wordBreak: "break-all",
                }}
              >
                {item.name}
              </div>
            </div>
          );
        })}
    </div>
  );
};

export const FileOpenDialog: React.FC<FileOpenDialogProps> = ({ isOpen, onClose, onSelect, title = "Open File", filter }) => {
  const [currentPath, setCurrentPath] = useState<string>(".");
  const [backStack, setBackStack] = useState<string[]>([]);
  const [forwardStack, setForwardStack] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [lastSelected, setLastSelected] = useState<string | null>(null);
  const [items, setItems] = useState<FileItem[]>([]);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [currentPathInput, setCurrentPathInput] = useState<string>(currentPath.replace(/\\/g, '/'));
  const searchInputRef = useRef<HTMLInputElement | null>(null);
  const viewMode = useSettingsStore(s => s.fileDialogViewMode);
  const setViewMode = useSettingsStore(s => s.setFileDialogViewMode);
  const persistedThumbSize = useSettingsStore(s => s.fileDialogThumbSize);
  const setPersistedThumbSize = useSettingsStore(s => s.setFileDialogThumbSize);
  const [thumbSize, setThumbSize] = useState<number>(persistedThumbSize);

  const visibleItems = items.filter(item => {
    if (item.isDirectory) return true;
    if (filter && !filter(item.name)) return false;
    if (!searchTerm.trim()) return true;
    return item.name.toLowerCase().includes(searchTerm.toLowerCase());
  });

  // listview 用的数据
  const treeNodes: TreeNodeInfo[] = visibleItems.map((item) => {
    const fullPath = item.path.replace(/\\/g, '/');
    return {
      id: fullPath,
      label: item.name,
      icon: item.isDirectory ? "folder-close" : "document",
      nodeData: { ...item, path: fullPath },
      hasCaret: false,
      isSelected: !item.isDirectory ? selectedPaths.has(fullPath) : false
    } as TreeNodeInfo;
  });

  useEffect(() => {
    setThumbSize(persistedThumbSize);
  }, [persistedThumbSize]);

  useEffect(() => {
    setCurrentPathInput(currentPath.replace(/\\/g, '/'));
  }, [currentPath]);

  useEffect(() => {
    const handle = setTimeout(() => {
      setPersistedThumbSize(thumbSize);
    }, 200);
    return () => clearTimeout(handle);
  }, [thumbSize, setPersistedThumbSize]);

  useEffect(() => {
    if (isOpen) {
      (async () => {
        try {
          const info = await getProjectInfo();
          if (info && info.editor && info.editor.resource_path) {
            const initial = info.editor.resource_path.replace(/\\/g, '/');
            tryChangePath(initial, false);
          } else {
            tryChangePath(currentPath, false);
          }
        } catch (e) {
          tryChangePath(currentPath, false);
        }
      })();
      setSelectedPaths(new Set());
      setLastSelected(null);
      setSearchTerm('');
      setBackStack([]);
      setForwardStack([]);
    }
  }, [isOpen]);

  const tryChangePath = async (newPath: string, addToHistory: boolean = true) => {
    const normalized = (newPath || '.').replace(/\\/g, '/');
    setIsLoading(true);
    try {
      const items = await listDir(normalized);
      setItems(items);
      if (addToHistory) {
        setBackStack(prev => [...prev, currentPath]);
        setForwardStack([]);
      }
      setCurrentPath(normalized);
      setCurrentPathInput(normalized);
    } catch (err: any) {
      const msg = err && err.message ? err.message : 'Failed to open path';
      toaster.show({ message: `Cannot open path: ${msg}`, intent: 'danger' });
      setCurrentPathInput(currentPath.replace(/\\/g, '/'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelect = (path: string, ctrlKey = false, shiftKey = false) => {
    setSelectedPaths(prev => {
      const next = new Set(prev);

      if (shiftKey && lastSelected && lastSelected !== path) {
        const fileIds = treeNodes
          .filter(n => {
            const d: any = n.nodeData;
            return d && !d.isDirectory;
          })
          .map(n => n.id as string);

        const a = fileIds.indexOf(lastSelected);
        const b = fileIds.indexOf(path);
        if (a !== -1 && b !== -1) {
          const [s, e] = a < b ? [a, b] : [b, a];
          if (!ctrlKey) next.clear();
          for (let i = s; i <= e; i++) {
            next.add(fileIds[i]);
          }
        } else {
          if (ctrlKey) {
            if (next.has(path)) next.delete(path); else next.add(path);
          } else {
            next.clear();
            next.add(path);
          }
        }
      } else if (ctrlKey) {
        if (next.has(path)) next.delete(path); else next.add(path);
      } else {
        next.clear();
        next.add(path);
      }

      setLastSelected(path);
      return next;
    });
  };

  const handleNodeClick = (node: TreeNodeInfo, _nodePath?: number[], e?: React.MouseEvent<HTMLElement>) => {
    const shiftKey = !!(e && e.shiftKey);
    const ctrlKey = !!(e && (e.ctrlKey || e.metaKey));
    const item = node.nodeData as any;
    if (item.isDirectory) {
      tryChangePath(item.path);
    } else {
      handleSelect(item.path, ctrlKey, shiftKey);
    }
  };

  const handleGoUp = () => {
    const normalized = currentPath.replace(/\\/g, '/');
    const parent = normalized.split('/').slice(0, -1).join("/") || ".";
    tryChangePath(parent);
  }

  const handleBack = () => {
    if (backStack.length === 0) return;
    const last = backStack[backStack.length - 1];
    setBackStack(prev => prev.slice(0, -1));
    setForwardStack(prev => [...prev, currentPath]);
    tryChangePath(last, false);
  }

  const handleForward = () => {
    if (forwardStack.length === 0) return;
    const next = forwardStack[forwardStack.length - 1];
    setForwardStack(prev => prev.slice(0, -1));
    setBackStack(prev => [...prev, currentPath]);
    tryChangePath(next, false);
  }

  const handleRefresh = () => {
    tryChangePath(currentPath, false);
  }

  const handleOpen = () => {
    onSelect(Array.from(selectedPaths));
    onClose();
  }

  return (
    <Dialog isOpen={isOpen} onClose={onClose} title={title} style={{ width: 900 }}>
      <div className={Classes.DIALOG_BODY}>
        <div style={{ marginBottom: 10, display: 'flex', gap: 10, alignItems: 'center' }}>
          <ButtonGroup minimal>
            <Button icon="chevron-left" onClick={handleBack} disabled={backStack.length === 0} minimal />
            <Button icon="chevron-right" onClick={handleForward} disabled={forwardStack.length === 0} minimal />
            <Button icon="refresh" onClick={handleRefresh} minimal />
            <Button icon="arrow-up" onClick={handleGoUp} disabled={currentPath === "."} minimal />
          </ButtonGroup>
          <div style={{ flex: 1, display: 'flex', gap: 8, alignItems: 'center' }}>
            <InputGroup
              small
              fill
              value={currentPathInput}
              onChange={(e) => setCurrentPathInput((e.target as HTMLInputElement).value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  tryChangePath(currentPathInput);
                }
              }}
              onBlur={() => {
                const p = (currentPathInput || '.').replace(/\\/g, '/');
                if (p !== currentPath) tryChangePath(p);
              }}
              style={{ flex: 1 }}
              
            />
            <ClearableInputGroup
              small
              leftIcon="search"
              placeholder="Search"
              value={searchTerm}
              onChange={(e) => setSearchTerm((e.target as HTMLInputElement).value)}
              style={{ width: 260 }}
              inputRef={(ref: HTMLInputElement | null) => { searchInputRef.current = ref; }}
              onClear={() => {
                setSearchTerm('');
                setTimeout(() => searchInputRef.current?.focus(), 0);
              }}
            />
          </div>
          <ButtonGroup minimal>
            <Button
              icon="list"
              active={viewMode === "list"}
              onClick={() => setViewMode("list")}
            />
            <Popover
                interactionKind={PopoverInteractionKind.HOVER}
              position={Position.BOTTOM}
              content={
                <div style={{ display: "flex", alignItems: "center", gap: 6, padding: 8 }}>
                  <span style={{ fontSize: 12 }}>Size</span>
                  <input
                    type="range"
                    min={64}
                    max={256}
                    value={thumbSize}
                    onChange={(e) => {
                      const value = Number(e.target.value);
                      if (!Number.isFinite(value) || value <= 0) {
                        throw new Error("Invalid thumbnail size");
                      }
                      setThumbSize(value);
                    }}
                  />
                </div>
              }
            >
              <Button
                icon="media"
                active={viewMode === "thumb"}
                onClick={() => setViewMode("thumb")}
              />
            </Popover>
          </ButtonGroup>
        </div>
        <div style={{ height: 400, overflow: 'auto', border: '1px solid #d1d8e0', position: 'relative' }}>
          {isLoading && (
            <div style={{
              position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
              background: 'rgba(255,255,255,0.7)', zIndex: 10,
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <Spinner size={20} />
            </div>
          )}
          {viewMode === "list" && (
            <Tree contents={treeNodes} onNodeClick={(node, nodePath, e) => handleNodeClick(node, nodePath, e)} />
          )}
          {viewMode === "thumb" && (
            <ThumbnailGrid
              items={visibleItems}
              selectedPaths={selectedPaths}
              thumbSize={thumbSize}
              onOpenDirectory={(p: string) => tryChangePath(p)}
              onToggleSelect={handleSelect}
            />
          )}
        </div>
      </div>
      <div className={Classes.DIALOG_FOOTER}>
        <div className={Classes.DIALOG_FOOTER_ACTIONS}>
          <div style={{ marginRight: 'auto' }}>
            {selectedPaths.size} files selected
          </div>
          <Button onClick={onClose}>Cancel</Button>
          <Button intent="primary" onClick={handleOpen} disabled={selectedPaths.size === 0}>Open</Button>
        </div>
      </div>
    </Dialog>
  );
};
