import React, { useState, useEffect, useMemo } from 'react';
import { useHorizontalScroll } from './hooks/useHorizontalScroll';
import { Icon, Tooltip, Menu, MenuItem } from '@blueprintjs/core';
import { useTranslation } from 'react-i18next';
import { COMMAND_ID, executeCommand } from '../editor/commands';
import { useAppStore } from '../editor/state';
import type { ITab } from '../editor/tabSystem/types';
import { useEditorDialogsContext } from '../editor/EditorDialogsContext';
import { getTabKind } from '../editor/tabSystem';

const TAB_MIN_WIDTH = 120;
const TAB_SIDE_PADDING = 20;
const TAB_GAP_AND_CLOSE = 24;
const TAB_FONT = '600 13px system-ui';

export const TabBar: React.FC = () => {
  const { t } = useTranslation();
  const { tabs, activeTabId, documents, setActiveTab } = useAppStore();
  const scrollRef = useHorizontalScroll();
  const { commandContext } = useEditorDialogsContext();

  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; tab: ITab } | null>(null);
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
      return Object.fromEntries(tabs.map((tab) => [tab.id, TAB_MIN_WIDTH]));
    }

    ctx.font = TAB_FONT;
    const naturalWidths = tabs.map((tab) => {
      const label = tab.label;
      const kindDef = getTabKind(tab.kind);
      const dirty = kindDef?.isDirty?.(tab) ?? false;
      const title = `${dirty ? '*' : ''}${label}`;
      const textWidth = Math.ceil(ctx.measureText(title).width);
      const iconExtra = kindDef?.icon ? 20 : 0;
      const natural = Math.max(TAB_MIN_WIDTH, textWidth + TAB_SIDE_PADDING + TAB_GAP_AND_CLOSE + iconExtra);
      return { id: tab.id, natural };
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
  }, [tabs, containerWidth]);

  useEffect(() => {
    if (!contextMenu) return;
    const onDown = () => setContextMenu(null);
    window.addEventListener('mousedown', onDown);
    return () => window.removeEventListener('mousedown', onDown);
  }, [contextMenu]);

  const handleTabClose = (tab: ITab, e: React.MouseEvent) => {
    e.stopPropagation();
    void executeCommand(COMMAND_ID.TAB_CLOSE, commandContext, { id: tab.id });
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
          const isActive = tab.id === activeTabId;
          const label = tab.label;
          const kindDef = getTabKind(tab.kind);
          const dirty = kindDef?.isDirty?.(tab) ?? false;
          const closable = tab.closable ?? true;

          return (
            <Tooltip content={label} key={tab.id} hoverOpenDelay={100}>
              <div
                onClick={() => setActiveTab(tab.id)}
                onContextMenu={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  setContextMenu({ x: e.clientX, y: e.clientY, tab });
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
                  width: tabWidths[tab.id] ?? TAB_MIN_WIDTH,
                  userSelect: 'none',
                  color: isActive ? '#182026' : '#5c7080'
                }}
              >
                {kindDef?.icon ? (
                  <span style={{ flexShrink: 0 }}>{kindDef.icon}</span>
                ) : null}
                <div style={{
                  flex: 1,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  fontWeight: isActive ? 600 : 400
                }}>
                  {`${dirty ? '*' : ''}${label}`}
                </div>
                {closable ? (
                  <Icon
                    icon="small-cross"
                    className="tab-close-btn"
                    onClick={(e) => handleTabClose(tab, e)}
                    style={{ opacity: 0.6 }}
                  />
                ) : null}
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
              void executeCommand(COMMAND_ID.TAB_CLOSE, commandContext, { id: contextMenu.tab.id });
              setContextMenu(null);
            }} />
            <MenuItem text={t('menuItem.closeAllDocuments')} onClick={() => {
              void executeCommand(COMMAND_ID.TAB_CLOSE_ALL, commandContext, undefined);
              setContextMenu(null);
            }} />
            <MenuItem text={t('tabBar.closeOthers')} onClick={() => {
              void executeCommand(COMMAND_ID.TAB_CLOSE_OTHERS, commandContext, { id: contextMenu.tab.id });
              setContextMenu(null);
            }} />
            {getTabKind(contextMenu.tab.kind)?.contextMenuItems?.(contextMenu.tab, commandContext)}
          </Menu>
        </div>
      ) : null}
    </>
  );
};
