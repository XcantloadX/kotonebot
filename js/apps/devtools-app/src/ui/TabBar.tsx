import React, { useState, useEffect, useMemo } from 'react';
import { useHorizontalScroll } from './hooks/useHorizontalScroll';
import { Icon, Tooltip, Menu, MenuItem, MenuDivider } from '@blueprintjs/core';
import { useTranslation } from 'react-i18next';
import { COMMAND_ID, executeCommand } from '../editor/commands';
import { useAppStore, tabId, type Tab } from '../editor/state';
import { useEditorDialogsContext } from '../editor/EditorDialogsContext';

const TAB_MIN_WIDTH = 120;
const TAB_SIDE_PADDING = 20;
const TAB_GAP_AND_CLOSE = 24;
const TAB_FONT = '600 13px system-ui';

function getTabLabel(tab: Tab): string {
  if (tab.kind === "welcome") return "";
  if (tab.kind === "conversion-result") return tab.label;
  return tab.docId.split("/").pop() || tab.docId;
}

function isTabDirty(tab: Tab, documents: Record<string, any>): boolean {
  if (tab.kind !== "document") return false;
  return documents[tab.docId]?.dirty ?? false;
}

export const TabBar: React.FC = () => {
  const { t } = useTranslation();
  const { tabs, activeTabId, documents, setActiveTab } = useAppStore();
  const scrollRef = useHorizontalScroll();
  const { commandContext } = useEditorDialogsContext();

  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; tabId: string } | null>(null);
  const [containerWidth, setContainerWidth] = useState(0);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const updateWidth = () => setContainerWidth(el.clientWidth);
    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    observer.observe(el);
    return () => observer.disconnect();
  }, [scrollRef, tabs.length]);

    // 计算 Tab 宽度。规则（类似于 Chrome Tab）：
    // 1. 若所有 Tab 的自然宽度之和小于容器宽度，则使用自然宽度。
    // 2. 否则按比例缩小，最小不小于 TAB_MIN_WIDTH。
  const tabWidths = useMemo(() => {
    if (tabs.length === 0) return {};

    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return Object.fromEntries(tabs.map((tab) => [tabId(tab), TAB_MIN_WIDTH]));
    }

    ctx.font = TAB_FONT;
    const naturalWidths = tabs.map((tab) => {
      const id = tabId(tab);
      const label = getTabLabel(tab);
      const dirty = isTabDirty(tab, documents);
      const title = `${dirty ? '*' : ''}${label}`;
      const textWidth = Math.ceil(ctx.measureText(title).width);
      const iconExtra = tab.kind === "welcome" ? 20 : 0;
      const natural = Math.max(TAB_MIN_WIDTH, textWidth + TAB_SIDE_PADDING + TAB_GAP_AND_CLOSE + iconExtra);
      return { id, natural };
    });

    const totalNatural = naturalWidths.reduce((sum, item) => sum + item.natural, 0);
    if (containerWidth > 0 && totalNatural <= containerWidth) {
      return Object.fromEntries(naturalWidths.map((item) => [item.id, item.natural]));
    }

    const shrinkCapacity = naturalWidths.reduce((sum, item) => sum + (item.natural - TAB_MIN_WIDTH), 0);
    const overflow = Math.max(0, totalNatural - containerWidth);

    if (containerWidth > 0 && overflow > 0 && overflow <= shrinkCapacity) {
      return Object.fromEntries(naturalWidths.map((item) => {
        const itemCapacity = item.natural - TAB_MIN_WIDTH;
        const shrink = shrinkCapacity > 0 ? Math.floor((itemCapacity / shrinkCapacity) * overflow) : 0;
        const width = Math.max(TAB_MIN_WIDTH, item.natural - shrink);
        return [item.id, width];
      }));
    }

    return Object.fromEntries(naturalWidths.map((item) => [item.id, TAB_MIN_WIDTH]));
  }, [tabs, containerWidth, documents]);

  useEffect(() => {
    if (!contextMenu) return;
    const onDown = () => setContextMenu(null);
    window.addEventListener('mousedown', onDown);
    return () => window.removeEventListener('mousedown', onDown);
  }, [contextMenu]);

  const handleTabClose = (tab: Tab, e: React.MouseEvent) => {
    e.stopPropagation();
    void executeCommand(COMMAND_ID.TAB_CLOSE, commandContext, { id: tabId(tab) });
  };

  return (
    <>
      <div
        ref={scrollRef}
        style={{
          display: 'flex',
          background: '#ced9e0',
          borderBottom: '1px solid #a7b6c2',
          overflowX: 'auto',
          height: 32,
          flex: '0 0 auto',
          alignItems: 'flex-end',
          scrollbarWidth: 'none'
        }}>
        {tabs.map(tab => {
          const id = tabId(tab);
          const isActive = id === activeTabId;
          const label = getTabLabel(tab);
          const dirty = isTabDirty(tab, documents);

          return (
            <Tooltip content={tab.kind === "welcome" ? t('welcome.tabLabel') : label} key={id} hoverOpenDelay={100}>
              <div
                onClick={() => setActiveTab(id)}
                onContextMenu={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setContextMenu({ x: e.clientX, y: e.clientY, tabId: id });
                }}
                style={{
                  padding: '5px 10px',
                  background: isActive ? '#f5f8fa' : '#ced9e0',
                  borderRight: '1px solid #a7b6c2',
                  borderTop: isActive ? '2px solid #106ba3' : '2px solid transparent',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  minWidth: TAB_MIN_WIDTH,
                  width: tabWidths[id] ?? TAB_MIN_WIDTH,
                  userSelect: 'none',
                  color: isActive ? '#182026' : '#5c7080'
                }}
              >
                {tab.kind === "welcome" ? (
                  <Icon icon="home" style={{ flexShrink: 0 }} />
                ) : null}
                <div style={{
                  flex: 1,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  fontWeight: isActive ? 600 : 400
                }}>
                  {tab.kind === "welcome" ? t('welcome.tabLabel') : `${dirty ? '*' : ''}${label}`}
                </div>
                <Icon
                  icon="small-cross"
                  className="tab-close-btn"
                  onClick={(e) => handleTabClose(tab, e)}
                  style={{ opacity: 0.6 }}
                />
              </div>
            </Tooltip>
          );
        })}
      </div>
      {contextMenu ? (
        <div
          style={{ position: 'fixed', left: contextMenu.x, top: contextMenu.y, zIndex: 2000 }}
          onContextMenu={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <Menu>
            <MenuItem text={t('menuItem.closeDocument')} onClick={() => {
              void executeCommand(COMMAND_ID.TAB_CLOSE, commandContext, { id: contextMenu.tabId });
              setContextMenu(null);
            }} />
            <MenuItem text={t('menuItem.closeAllDocuments')} onClick={() => {
              void executeCommand(COMMAND_ID.TAB_CLOSE_ALL, commandContext, undefined);
              setContextMenu(null);
            }} />
            <MenuItem text={t('tabBar.closeOthers')} onClick={() => {
              void executeCommand(COMMAND_ID.TAB_CLOSE_OTHERS, commandContext, { id: contextMenu.tabId });
              setContextMenu(null);
            }} />
            {tabs.find(t => tabId(t) === contextMenu.tabId)?.kind === "document" ? (
              <>
                <MenuDivider />
                <MenuItem text={t('tabBar.revealInExplorer')} onClick={() => {
                  const doc = documents[contextMenu.tabId];
                  if (doc) {
                    void executeCommand(COMMAND_ID.FILE_REVEAL_IN_EXPLORER, commandContext, { path: doc.image.path });
                  }
                  setContextMenu(null);
                }} />
              </>
            ) : null}
          </Menu>
        </div>
      ) : null}
    </>
  );
};
