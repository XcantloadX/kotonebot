import React, { useRef, useState } from 'react';
import { usePanelStore, PanelId } from '../editor/panelStore';

export interface PanelView {
  id: string;
  title: string;
  content: React.ReactNode;
}

interface PanelContainerProps {
  panelId: PanelId;
  views: Record<string, PanelView>;
}

// Module-level drag state so cross-panel DnD works without context
let dragState: { tabId: string; fromPanelId: PanelId } | null = null;

export const PanelContainer: React.FC<PanelContainerProps> = ({ panelId, views }) => {
  // Derive ordered tab list directly from tabConfigs (stable selector)
  const tabIds = usePanelStore((s) =>
    Object.values(s.tabConfigs)
      .filter((c) => c.panelId === panelId)
      .sort((a, b) => a.order - b.order)
      .map((c) => c.id),
  );
  const activeTabId = usePanelStore((s) => s.activeTabIds[panelId]);
  const setActiveTab = usePanelStore((s) => s.setActiveTab);
  const reorderTab = usePanelStore((s) => s.reorderTab);
  const moveTab = usePanelStore((s) => s.moveTab);

  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const tabBarRef = useRef<HTMLDivElement>(null);

  const handleTabDragStart = (e: React.DragEvent, tabId: string) => {
    dragState = { tabId, fromPanelId: panelId };
    e.dataTransfer.effectAllowed = 'move';
    // Set a generic text so browsers allow the drag
    e.dataTransfer.setData('text/plain', tabId);
  };

  const handleTabDragEnd = () => {
    dragState = null;
    setDragOverIndex(null);
    setIsDragOver(false);
  };

  const getInsertIndex = (e: React.DragEvent): number => {
    if (!tabBarRef.current) return tabIds.length;
    const tabElements = tabBarRef.current.querySelectorAll<HTMLElement>('[data-tab-id]');
    let insertIdx = tabIds.length;
    tabElements.forEach((el, i) => {
      const rect = el.getBoundingClientRect();
      const mid = rect.left + rect.width / 2;
      if (e.clientX < mid && insertIdx === tabIds.length) {
        insertIdx = i;
      }
    });
    return insertIdx;
  };

  const handleTabBarDragOver = (e: React.DragEvent) => {
    if (!dragState) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setIsDragOver(true);
    setDragOverIndex(getInsertIndex(e));
  };

  const handleTabBarDragLeave = (e: React.DragEvent) => {
    // Only clear if we left the tab bar entirely
    if (!tabBarRef.current?.contains(e.relatedTarget as Node)) {
      setDragOverIndex(null);
      setIsDragOver(false);
    }
  };

  const handleTabBarDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (!dragState) return;
    const { tabId, fromPanelId } = dragState;
    const toIndex = getInsertIndex(e);
    if (fromPanelId === panelId) {
      reorderTab(tabId, toIndex);
    } else {
      moveTab(tabId, panelId, toIndex);
    }
    dragState = null;
    setDragOverIndex(null);
    setIsDragOver(false);
  };

  if (tabIds.length === 0) {
    return (
      <div
        className="kb-panel-empty"
        onDragOver={handleTabBarDragOver}
        onDragLeave={handleTabBarDragLeave}
        onDrop={handleTabBarDrop}
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#8ea1b3',
          fontSize: 12,
          minHeight: 40,
          border: isDragOver ? '2px dashed #5c7cfa' : '2px dashed transparent',
          borderRadius: 4,
          transition: 'border-color 0.15s',
        }}
      >
        Drop tabs here
      </div>
    );
  }

  const currentView = activeTabId ? views[activeTabId] : null;

  return (
    <div className="kb-panel-container">
      {/* Tab bar */}
      <div
        ref={tabBarRef}
        className="kb-panel-tabbar"
        onDragOver={handleTabBarDragOver}
        onDragLeave={handleTabBarDragLeave}
        onDrop={handleTabBarDrop}
      >
        {tabIds.map((tabId, idx) => {
          const view = views[tabId];
          if (!view) return null;
          const isActive = tabId === activeTabId;
          const showInsertBefore = dragOverIndex === idx;
          const showInsertAfter =
            dragOverIndex === tabIds.length && idx === tabIds.length - 1;

          return (
            <React.Fragment key={tabId}>
              {showInsertBefore && (
                <div className="kb-panel-tab-insert-indicator" />
              )}
              <div
                data-tab-id={tabId}
                className={`kb-panel-tab${isActive ? ' kb-panel-tab--active' : ''}`}
                draggable
                onDragStart={(e) => handleTabDragStart(e, tabId)}
                onDragEnd={handleTabDragEnd}
                onClick={() => setActiveTab(panelId, tabId)}
                title={view.title}
              >
                {view.title}
              </div>
              {showInsertAfter && (
                <div className="kb-panel-tab-insert-indicator" />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Content area */}
      <div className="kb-panel-content">
        {tabIds.map((tabId) => {
          const view = views[tabId];
          if (!view) return null;
          return (
            <div
              key={tabId}
              className="kb-panel-view"
              style={{ display: tabId === activeTabId ? 'flex' : 'none' }}
            >
              {view.content}
            </div>
          );
        })}
        {!currentView && (
          <div
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#8ea1b3',
              fontSize: 12,
            }}
          >
            No view selected
          </div>
        )}
      </div>
    </div>
  );
};
