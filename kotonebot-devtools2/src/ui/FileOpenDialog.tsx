import React, { useState, useEffect } from 'react';
import { Dialog, Classes, Button, Tree, TreeNodeInfo, Spinner } from '@blueprintjs/core';
import { listDir, getProjectInfo } from '../api/fs';

interface FileOpenDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (paths: string[]) => void;
  title?: string;
  filter?: (name: string) => boolean;
}

export const FileOpenDialog: React.FC<FileOpenDialogProps> = ({ isOpen, onClose, onSelect, title = "Open File", filter }) => {
  const [currentPath, setCurrentPath] = useState<string>(".");
  const [nodes, setNodes] = useState<TreeNodeInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPaths, setSelectedPaths] = useState<Set<string>>(new Set());
  const [lastSelected, setLastSelected] = useState<string | null>(null);

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
          <Tree contents={nodes} onNodeClick={(node, nodePath, e) => handleNodeClick(node, nodePath, e)} />
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
