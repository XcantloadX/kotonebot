import React, { useState, useEffect } from 'react';
import { Dialog, Classes, Button, ButtonGroup, Tree, TreeNodeInfo, Spinner, Popover, PopoverInteractionKind, Position } from '@blueprintjs/core';
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
  filter?: (name: string) => boolean;
  selectedPaths: Set<string>;
  thumbSize: number;
  onOpenDirectory: (path: string) => void;
  onToggleSelect: (path: string, ctrlKey: boolean, shiftKey: boolean) => void;
}

const ThumbnailGrid: React.FC<ThumbnailGridProps> = ({
  items,
  filter,
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
      {items
        .filter(item => item.isDirectory || (filter ? filter(item.name) : true))
        .map((item) => {
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
  const [nodes, setNodes] = useState<TreeNodeInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [lastSelected, setLastSelected] = useState<string | null>(null);
  const [items, setItems] = useState<FileItem[]>([]);
  const viewMode = useSettingsStore(s => s.fileDialogViewMode);
  const setViewMode = useSettingsStore(s => s.setFileDialogViewMode);
  const persistedThumbSize = useSettingsStore(s => s.fileDialogThumbSize);
  const setPersistedThumbSize = useSettingsStore(s => s.setFileDialogThumbSize);
  const [thumbSize, setThumbSize] = useState<number>(persistedThumbSize);

  useEffect(() => {
    setThumbSize(persistedThumbSize);
  }, [persistedThumbSize]);

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
            setCurrentPath(info.editor.resource_path.replace(/\\/g, '/'));
          }
        } catch (e) {
          // fallback to currentPath
        }
      })();
      setSelectedPaths(new Set());
      setLastSelected(null);
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      loadDir(currentPath);
    }
  }, [isOpen, currentPath]);

  const loadDir = async (path: string) => {
    setIsLoading(true);
    try {
      const items = await listDir(path);
      setItems(items);
      const treeNodes: TreeNodeInfo[] = items
        .filter(item => item.isDirectory || (filter ? filter(item.name) : true))
        .map((item) => {
          const fullPath = item.path.replace(/\\/g, '/');
          return {
            id: fullPath,
            label: item.name,
            icon: item.isDirectory ? "folder-close" : "document",
            nodeData: { ...item, path: fullPath },
            hasCaret: false,
            isSelected: !item.isDirectory ? selectedPaths.has(fullPath) : false
          };
        });

      if (path !== "." && path !== "") {
        treeNodes.unshift({
          id: "parent",
          label: "..",
          icon: "folder-open",
          nodeData: { isDirectory: true, path: ".." },
          hasCaret: false
        });
      }

      setNodes(treeNodes);
    } catch (e) {
      console.error("Failed to list dir", e);
    } finally {
      setIsLoading(false);
    }
  };
  const syncNodeSelection = (nextSelected: Set<string>) => {
    setNodes(prev => prev.map(node => {
      const data: any = node.nodeData;
      if (data && !data.isDirectory && node.id !== "parent") {
        const id = node.id as string;
        return {
          ...node,
          isSelected: nextSelected.has(id)
        };
      }
      return node;
    }));
  };

  const handleSelect = (path: string, ctrlKey = false, shiftKey = false) => {
    setSelectedPaths(prev => {
      const next = new Set(prev);

      if (shiftKey && lastSelected && lastSelected !== path) {
        const fileIds = nodes
          .filter(n => {
            const d: any = n.nodeData;
            return d && !d.isDirectory && n.id !== "parent";
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
      syncNodeSelection(next);
      return next;
    });
  };

  const handleNodeClick = (node: TreeNodeInfo, _nodePath?: number[], e?: React.MouseEvent<HTMLElement>) => {
    const shiftKey = !!(e && e.shiftKey);
    const ctrlKey = !!(e && (e.ctrlKey || e.metaKey));
    const item = node.nodeData as any;
    if (node.id === "parent") {
      handleGoUp();
      return;
    }

    if (item.isDirectory) {
      setCurrentPath(item.path);
    } else {
      handleSelect(item.path, ctrlKey, shiftKey);
    }
  };

  const handleGoUp = () => {
    const normalized = currentPath.replace(/\\/g, '/');
    const parent = normalized.split('/').slice(0, -1).join("/") || ".";
    setCurrentPath(parent);
  }

  const handleOpen = () => {
    onSelect(Array.from(selectedPaths));
    onClose();
  }

  return (
    <Dialog isOpen={isOpen} onClose={onClose} title={title} style={{ width: 600 }}>
      <div className={Classes.DIALOG_BODY}>
        <div style={{ marginBottom: 10, display: 'flex', gap: 10, alignItems: 'center' }}>
          <Button icon="arrow-up" onClick={handleGoUp} disabled={currentPath === "."} minimal />
          <div style={{ wordBreak: 'break-all', flex: 1 }}>{currentPath.replace(/\\/g, '/')}</div>
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
            <Tree contents={nodes} onNodeClick={(node, nodePath, e) => handleNodeClick(node, nodePath, e)} />
          )}
          {viewMode === "thumb" && (
            <ThumbnailGrid
              items={items}
              filter={filter}
              selectedPaths={selectedPaths}
              thumbSize={thumbSize}
              onOpenDirectory={setCurrentPath}
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
