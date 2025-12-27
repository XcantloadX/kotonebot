import React, { useState, useEffect } from 'react';
import { useHorizontalScroll } from './hooks/useHorizontalScroll';
import { Button, Icon, Tooltip, Dialog, Menu, MenuItem } from '@blueprintjs/core';
import { useAppStore } from '../editor/state';

export const TabBar: React.FC = () => {
    const { documents, activeDocumentId, setActiveDocument, closeDocument, markAsSaved } = useAppStore();
    const scrollRef = useHorizontalScroll();

    const docList = Object.values(documents);
    const [closingDocId, setClosingDocId] = useState<string | null>(null);
    const [pendingCloseQueue, setPendingCloseQueue] = useState<string[]>([]);
    const [contextMenu, setContextMenu] = useState<{ x: number; y: number; docId: string } | null>(null);

    console.log('TabBar rendering, docs:', docList.length);

    function enqueueClosures(ids: string[]) {
        if (!ids || ids.length === 0) return;
        const queue = [...ids];
        setPendingCloseQueue(queue);
        // start processing immediately
        processQueue(queue);
    }

    function processQueue(queueParam?: string[]) {
        const queue = queueParam ?? pendingCloseQueue;
        if (!queue || queue.length === 0) return;
        const id = queue[0];
        const doc = documents[id];
        if (!doc) {
            const rest = queue.slice(1);
            setPendingCloseQueue(rest);
            processQueue(rest);
            return;
        }
        if (doc.dirty) {
            setClosingDocId(id);
            return;
        }
        // close and continue
        closeDocument(id);
        const rest = queue.slice(1);
        setPendingCloseQueue(rest);
        if (rest.length > 0) {
            processQueue(rest);
        }
    }

    function advanceQueueAfterDialog() {
        setPendingCloseQueue((q) => {
            const [, ...rest] = q;
            // close next items that are not dirty immediately
            setTimeout(() => processQueue(rest), 0);
            setClosingDocId(null);
            return rest;
        });
    }

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
                                    minWidth: 100,
                                    maxWidth: 200,
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
                                        if (doc.dirty) {
                                            setClosingDocId(doc.id);
                                        } else {
                                            closeDocument(doc.id);
                                        }
                                    }}
                                    style={{ opacity: 0.6 }}
                                />
                            </div>
                        </Tooltip>
                    );
                })}
            </div>
            <Dialog
                isOpen={!!closingDocId}
                onClose={() => setClosingDocId(null)}
                title="Unsaved changes"
            >
                <div style={{ padding: 16 }}>
                    <div style={{ marginBottom: 12 }}>
                        {closingDocId ? (
                            <>File "{closingDocId.split(/[/\\]/).pop()}" has unsaved changes. Save before closing?</>
                        ) : null}
                    </div>
                    <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                        <Button
                            onClick={() => {
                                if (!closingDocId) return;
                                setActiveDocument(closingDocId);
                                markAsSaved();
                                closeDocument(closingDocId);
                                // advance queue if any
                                advanceQueueAfterDialog();
                            }}
                            intent="primary"
                        >
                            Save
                        </Button>
                        <Button
                            onClick={() => {
                                if (!closingDocId) return;
                                closeDocument(closingDocId);
                                // advance queue if any
                                advanceQueueAfterDialog();
                            }}
                        >
                            Don't Save
                        </Button>
                        <Button onClick={() => setClosingDocId(null)}>Cancel</Button>
                    </div>
                </div>
            </Dialog>
            {contextMenu ? (
                <div
                    style={{ position: 'fixed', left: contextMenu.x, top: contextMenu.y, zIndex: 2000 }}
                    onContextMenu={(e) => e.stopPropagation()}
                    onMouseDown={(e) => e.stopPropagation()}
                >
                    <Menu>
                        <MenuItem text="Close" onClick={() => {
                            const id = contextMenu.docId;
                            const doc = documents[id];
                            if (doc) {
                                if (doc.dirty) {
                                    setClosingDocId(id);
                                } else {
                                    closeDocument(id);
                                }
                            }
                            setContextMenu(null);
                        }} />
                        <MenuItem text="Close All" onClick={() => {
                            const ids = Object.keys(documents);
                            enqueueClosures(ids);
                            setContextMenu(null);
                        }} />
                        <MenuItem text="Close Others" onClick={() => {
                            const id = contextMenu.docId;
                            const ids = Object.keys(documents).filter(i => i !== id);
                            enqueueClosures(ids);
                            setContextMenu(null);
                        }} />
                    </Menu>
                </div>
            ) : null}
        </>
    );

};
