import React, { useState, useEffect, useMemo } from 'react';
import { useHorizontalScroll } from './hooks/useHorizontalScroll';
import { Icon, Tooltip, Menu, MenuItem } from '@blueprintjs/core';
import { COMMAND_ID, executeCommand } from '../editor/commands';
import { useAppStore } from '../editor/state';

const TAB_MIN_WIDTH = 120;
const TAB_SIDE_PADDING = 20;
const TAB_GAP_AND_CLOSE = 24;
const TAB_FONT = '600 13px system-ui';


export const TabBar: React.FC = () => {
    const { documents, activeDocumentId, setActiveDocument } = useAppStore();
    const scrollRef = useHorizontalScroll();
    const commandContext = useMemo(() => ({ ui: {} }), []);

    const docList = Object.values(documents);
    const [contextMenu, setContextMenu] = useState<{ x: number; y: number; docId: string } | null>(null);
    const [containerWidth, setContainerWidth] = useState(0);

    useEffect(() => {
        const el = scrollRef.current;
        if (!el) return;
        const updateWidth = () => setContainerWidth(el.clientWidth);
        updateWidth();
        const observer = new ResizeObserver(updateWidth);
        observer.observe(el);
        return () => observer.disconnect();
    }, [scrollRef, docList.length]);

    // 计算 Tab 宽度。规则（类似于 Chrome Tab）：
    // 1. 若所有 Tab 的自然宽度之和小于容器宽度，则使用自然宽度。
    // 2. 否则按比例缩小，最小不小于 TAB_MIN_WIDTH。
    const tabWidths = useMemo(() => {
        if (docList.length === 0) return {};

        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        if (!ctx) {
            return Object.fromEntries(docList.map((doc) => [doc.id, TAB_MIN_WIDTH]));
        }

        ctx.font = TAB_FONT;
        const naturalWidths = docList.map((doc) => {
            const name = doc.id.split(/[/\\]/).pop() || doc.id;
            const title = `${doc.dirty ? '*' : ''}${name}`;
            const textWidth = Math.ceil(ctx.measureText(title).width);
            const natural = Math.max(TAB_MIN_WIDTH, textWidth + TAB_SIDE_PADDING + TAB_GAP_AND_CLOSE);
            return { id: doc.id, natural };
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
    }, [docList, containerWidth, activeDocumentId]);

    useEffect(() => {
        if (!contextMenu) return;
        const onDown = () => setContextMenu(null);
        window.addEventListener('mousedown', onDown);
        return () => window.removeEventListener('mousedown', onDown);
    }, [contextMenu]);

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
                {docList.map(doc => {
                    const isActive = doc.id === activeDocumentId;
                    const name = doc.id.split(/[/\\]/).pop() || doc.id;

                    return (
                        <Tooltip content={name} key={doc.id} hoverOpenDelay={100}>
                            <div
                                onClick={() => setActiveDocument(doc.id)}
                                onContextMenu={(e) => {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    setContextMenu({ x: e.clientX, y: e.clientY, docId: doc.id });
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
                                    width: tabWidths[doc.id] ?? TAB_MIN_WIDTH,
                                    userSelect: 'none',
                                    color: isActive ? '#182026' : '#5c7080'
                                }}
                            >
                                <div style={{
                                    flex: 1,
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                    fontWeight: isActive ? 600 : 400
                                }}>
                                    {doc.dirty ? '*' : ''}{name}
                                </div>
                                    <Icon
                                    icon="small-cross"
                                    className="tab-close-btn"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        void executeCommand(COMMAND_ID.DOCUMENT_CLOSE, commandContext, { id: doc.id });
                                    }}
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
                        <MenuItem text="Close" onClick={() => {
                            const id = contextMenu.docId;
                            void executeCommand(COMMAND_ID.DOCUMENT_CLOSE, commandContext, { id });
                            setContextMenu(null);
                        }} />
                        <MenuItem text="Close All" onClick={() => {
                            const ids = Object.keys(documents);
                            void executeCommand(COMMAND_ID.DOCUMENT_CLOSE_MANY, commandContext, { ids });
                            setContextMenu(null);
                        }} />
                        <MenuItem text="Close Others" onClick={() => {
                            const id = contextMenu.docId;
                            const ids = Object.keys(documents).filter(i => i !== id);
                            void executeCommand(COMMAND_ID.DOCUMENT_CLOSE_MANY, commandContext, { ids });
                            setContextMenu(null);
                        }} />
                    </Menu>
                </div>
            ) : null}
        </>
    );

};
