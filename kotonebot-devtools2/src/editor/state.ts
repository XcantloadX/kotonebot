import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { Patch, applyPatches, current, enablePatches, produceWithPatches } from 'immer';
import { DefinitionV2, MetaV2, ResourceType } from '../model/metaV2';
import { PrefabSchema } from '../model/prefabSchema';
import { writeText } from '../api/fs';
import { toaster } from '../ui/toaster';
import { useSymbolIndexStore } from './symbolIndexStore';

enablePatches();

const HISTORY_LIMIT = 200;
const HISTORY_MERGE_WINDOW_MS = 400;

export type ToolType = "select" | "rect" | "point";

export type InteractionMode =
  | { kind: "idle" }
  | { kind: "picking"; definitionId: string; propKey: string; tool: "rect" | "point" | "image" }
  | { kind: "creating-prefab"; prefab_id: string; propKey: string; tool: "rect" | "point" | "image" };

export interface DocumentState {
  id: string; // Usually the image path
  image: { path: string; width: number; height: number; url: string };
  meta: { path: string; data: MetaV2 } | null;
  
  selection: { definitionId: string } | null;
  mode: InteractionMode;
  dirty: boolean;
  
  history: {
    entries: HistoryEntry[];
    cursor: number;
    saveCursor: number | null;
    transaction: HistoryTransaction | null;
  };
  
  view?: { x: number; y: number; scale: number };
}

export interface UpdateMetaOptions {
  label?: string;
  mergeKey?: string;
  forceNewEntry?: boolean;
}

interface HistoryEntry {
  label: string;
  mergeKey?: string;
  timestamp: number;
  patches: Patch[];
  inversePatches: Patch[];
}

interface HistoryTransaction {
  label: string;
  mergeKey?: string;
  startedAt: number;
  patches: Patch[];
  inversePatches: Patch[];
}

export interface FocusSpotlightState {
  id: string;
  centerScreen: { x: number; y: number };
  radius: number;
  enterMs: number;
  holdMs: number;
  exitMs: number;
}

export interface DefinitionClipboard {
  sourceDefinitionId: string;
  definition: DefinitionV2;
}

interface AppState {
  documents: Record<string, DocumentState>;
  activeDocumentId: string | null;
  focusSpotlight: FocusSpotlightState | null;
  definitionClipboard: DefinitionClipboard | null;
  
  prefabSchema: PrefabSchema | null;
  activeTool: ToolType;
  activeResourceType: ResourceType;

  // Actions
  openDocument: (path: string, width: number, height: number) => void;
  closeDocument: (id: string) => void;
  renameDocument: (oldId: string, newId: string) => void;
  renameDocuments: (renames: Array<{ oldId: string; newId: string }>) => void;
  setActiveDocument: (id: string) => void;
  setViewState: (id: string, view: { x: number; y: number; scale: number }) => void;
  
  setPrefabSchema: (schema: PrefabSchema) => void;
  setActiveTool: (tool: ToolType) => void;
  setActiveResourceType: (type: ResourceType) => void;
  setDefinitionClipboard: (clipboard: DefinitionClipboard | null) => void;

  // Active Document Actions
  setSelection: (definitionId: string | null) => void;
  setMode: (mode: InteractionMode) => void;
  setActiveMeta: (docId: string, data: MetaV2) => void;
  updateMeta: (updater: (draft: MetaV2) => void, options?: UpdateMetaOptions) => void;
  beginMetaTransaction: (options: { label: string; mergeKey?: string }) => void;
  commitMetaTransaction: () => void;
  cancelMetaTransaction: () => void;
  
  undo: () => void;
  redo: () => void;
  saveActiveDocument: () => Promise<void>;
  saveAllDocuments: () => Promise<number>;
  showFocusSpotlight: (spotlight: FocusSpotlightState) => void;
  clearFocusSpotlight: () => void;
}

export const useAppStore = create<AppState>()(
  immer((set) => ({
    documents: {},
    activeDocumentId: null,
    focusSpotlight: null,
    definitionClipboard: null,
    prefabSchema: null,
    activeTool: "select",
    activeResourceType: "hint-box",

    openDocument: (path, width, height) => set((state) => {
      if (state.documents[path]) {
        state.activeDocumentId = path;
        return;
      }
      
      state.documents[path] = {
        id: path,
        image: { path, width, height, url: `/api/image?path=${encodeURIComponent(path)}` },
        meta: null,
        selection: null,
        mode: { kind: "idle" },
        dirty: false,
        history: {
          entries: [],
          cursor: 0,
          saveCursor: 0,
          transaction: null,
        }
      };
      state.activeDocumentId = path;
    }),

    closeDocument: (id) => set((state) => {
      delete state.documents[id];
      if (state.activeDocumentId === id) {
        const ids = Object.keys(state.documents);
        state.activeDocumentId = ids.length > 0 ? ids[ids.length - 1] : null;
      }
    }),

    renameDocument: (oldId, newId) => set((state) => {
      const doc = state.documents[oldId];
      if (!doc) {
        throw new Error(`Document not found: ${oldId}`);
      }
      if (state.documents[newId]) {
        throw new Error(`Document already exists: ${newId}`);
      }
      const nextMetaPath = `${newId}.json`;
      delete state.documents[oldId];
      doc.id = newId;
      doc.image.path = newId;
      doc.image.url = `/api/image?path=${encodeURIComponent(newId)}`;
      if (!doc.meta) {
        throw new Error(`Document meta is not loaded: ${oldId}`);
      }
      doc.meta.path = nextMetaPath;
      state.documents[newId] = doc;
      if (state.activeDocumentId === oldId) {
        state.activeDocumentId = newId;
      }
    }),

    renameDocuments: (renames) => set((state) => {
      if (renames.length === 0) {
        return;
      }
      const oldSet = new Set<string>();
      const newSet = new Set<string>();
      for (const item of renames) {
        if (oldSet.has(item.oldId)) {
          throw new Error(`Duplicate oldId in rename list: ${item.oldId}`);
        }
        if (newSet.has(item.newId)) {
          throw new Error(`Duplicate newId in rename list: ${item.newId}`);
        }
        oldSet.add(item.oldId);
        newSet.add(item.newId);
      }
      for (const item of renames) {
        const doc = state.documents[item.oldId];
        if (!doc) {
          throw new Error(`Document not found: ${item.oldId}`);
        }
        const existing = state.documents[item.newId];
        if (existing && !oldSet.has(item.newId)) {
          throw new Error(`Document already exists: ${item.newId}`);
        }
      }
      const movingDocs: Array<{ oldId: string; newId: string; doc: DocumentState }> = [];
      for (const item of renames) {
        const doc = state.documents[item.oldId];
        if (!doc) {
          throw new Error(`Document not found: ${item.oldId}`);
        }
        delete state.documents[item.oldId];
        movingDocs.push({ oldId: item.oldId, newId: item.newId, doc });
      }
      for (const item of movingDocs) {
        item.doc.id = item.newId;
        item.doc.image.path = item.newId;
        item.doc.image.url = `/api/image?path=${encodeURIComponent(item.newId)}`;
        if (!item.doc.meta) {
          throw new Error(`Document meta is not loaded: ${item.oldId}`);
        }
        item.doc.meta.path = `${item.newId}.json`;
        state.documents[item.newId] = item.doc;
      }
      if (state.activeDocumentId) {
        const activeRename = movingDocs.find((item) => item.oldId === state.activeDocumentId);
        if (activeRename) {
          state.activeDocumentId = activeRename.newId;
        }
      }
    }),

    setActiveDocument: (id) => set((state) => {
      if (state.documents[id]) {
        state.activeDocumentId = id;
      }
    }),

    setViewState: (id, view) => set((state) => {
      if (state.documents[id]) {
        state.documents[id].view = view;
      }
    }),

    setPrefabSchema: (schema) => set({ prefabSchema: schema }),
    
    setActiveTool: (tool) => set((state) => {
        state.activeTool = tool;
        if (state.activeDocumentId && state.documents[state.activeDocumentId]) {
             state.documents[state.activeDocumentId].mode = { kind: "idle" };
        }
    }),
    
    setActiveResourceType: (type) => set({ activeResourceType: type }),

    setDefinitionClipboard: (clipboard) => set({ definitionClipboard: clipboard }),

    showFocusSpotlight: (spotlight) => set({ focusSpotlight: spotlight }),

    clearFocusSpotlight: () => set({ focusSpotlight: null }),

    setSelection: (selection) => set((state) => {
      if (state.activeDocumentId && state.documents[state.activeDocumentId]) {
        state.documents[state.activeDocumentId].selection = selection ? { definitionId: selection } : null;
      }
    }),

    setMode: (mode) => set((state) => {
      if (state.activeDocumentId && state.documents[state.activeDocumentId]) {
        state.documents[state.activeDocumentId].mode = mode;
      }
    }),

    setActiveMeta: (docId, data) => set((state) => {
       if (state.documents[docId]) {
           const doc = state.documents[docId];
           doc.meta = { path: docId + ".json", data };
           doc.dirty = false;
           doc.history = {
             entries: [],
             cursor: 0,
             saveCursor: 0,
             transaction: null,
           };
       }
    }),

    updateMeta: (updater, options) => set((state) => {
      if (state.activeDocumentId && state.documents[state.activeDocumentId]) {
        const doc = state.documents[state.activeDocumentId];
        if (doc.meta) {
            const base = current(doc.meta.data);
            const [next, patches, inversePatches] = produceWithPatches(base, updater);
            if (patches.length === 0) {
              return;
            }

            doc.meta.data = next;

            const transaction = doc.history.transaction;
            if (transaction) {
              transaction.patches.push(...patches);
              transaction.inversePatches.unshift(...inversePatches);
              doc.dirty = doc.history.saveCursor !== doc.history.cursor;
              return;
            }

            if (doc.history.cursor < doc.history.entries.length) {
              doc.history.entries.splice(doc.history.cursor);
              if (doc.history.saveCursor !== null && doc.history.saveCursor > doc.history.cursor) {
                doc.history.saveCursor = null;
              }
            }

            const now = Date.now();
            const shouldTryMerge = !!options?.mergeKey && !options?.forceNewEntry;
            if (shouldTryMerge && doc.history.cursor > 0) {
              const previous = doc.history.entries[doc.history.cursor - 1];
              if (
                previous &&
                previous.mergeKey === options?.mergeKey &&
                now - previous.timestamp <= HISTORY_MERGE_WINDOW_MS
              ) {
                previous.patches.push(...patches);
                previous.inversePatches.unshift(...inversePatches);
                previous.timestamp = now;
                doc.dirty = doc.history.saveCursor !== doc.history.cursor;
                return;
              }
            }

            doc.history.entries.push({
              label: options?.label ?? "Edit",
              mergeKey: options?.mergeKey,
              timestamp: now,
              patches,
              inversePatches,
            });
            doc.history.cursor += 1;

            if (doc.history.entries.length > HISTORY_LIMIT) {
              const overflow = doc.history.entries.length - HISTORY_LIMIT;
              doc.history.entries.splice(0, overflow);
              doc.history.cursor = Math.max(0, doc.history.cursor - overflow);
              if (doc.history.saveCursor !== null) {
                if (doc.history.saveCursor < overflow) {
                  doc.history.saveCursor = null;
                } else {
                  doc.history.saveCursor -= overflow;
                }
              }
            }

            doc.dirty = doc.history.saveCursor !== doc.history.cursor;
        }
      }
    }),

    beginMetaTransaction: ({ label, mergeKey }) => set((state) => {
      if (state.activeDocumentId && state.documents[state.activeDocumentId]) {
        const doc = state.documents[state.activeDocumentId];
        if (!doc.meta) {
          throw new Error("Cannot begin transaction: active document has no meta");
        }
        if (doc.history.transaction) {
          throw new Error("History transaction already active");
        }
        doc.history.transaction = {
          label,
          mergeKey,
          startedAt: Date.now(),
          patches: [],
          inversePatches: [],
        };
      }
    }),

    commitMetaTransaction: () => set((state) => {
      if (state.activeDocumentId && state.documents[state.activeDocumentId]) {
        const doc = state.documents[state.activeDocumentId];
        const transaction = doc.history.transaction;
        if (!transaction) {
          throw new Error("Cannot commit transaction: no active transaction");
        }
        doc.history.transaction = null;

        if (transaction.patches.length === 0) {
          return;
        }

        if (doc.history.cursor < doc.history.entries.length) {
          doc.history.entries.splice(doc.history.cursor);
          if (doc.history.saveCursor !== null && doc.history.saveCursor > doc.history.cursor) {
            doc.history.saveCursor = null;
          }
        }

        const now = Date.now();
        const shouldTryMerge = !!transaction.mergeKey;
        if (shouldTryMerge && doc.history.cursor > 0) {
          const previous = doc.history.entries[doc.history.cursor - 1];
          if (
            previous &&
            previous.mergeKey === transaction.mergeKey &&
            now - previous.timestamp <= HISTORY_MERGE_WINDOW_MS
          ) {
            previous.patches.push(...transaction.patches);
            previous.inversePatches.unshift(...transaction.inversePatches);
            previous.timestamp = now;
            doc.dirty = doc.history.saveCursor !== doc.history.cursor;
            return;
          }
        }

        doc.history.entries.push({
          label: transaction.label,
          mergeKey: transaction.mergeKey,
          timestamp: now,
          patches: transaction.patches,
          inversePatches: transaction.inversePatches,
        });
        doc.history.cursor += 1;

        if (doc.history.entries.length > HISTORY_LIMIT) {
          const overflow = doc.history.entries.length - HISTORY_LIMIT;
          doc.history.entries.splice(0, overflow);
          doc.history.cursor = Math.max(0, doc.history.cursor - overflow);
          if (doc.history.saveCursor !== null) {
            if (doc.history.saveCursor < overflow) {
              doc.history.saveCursor = null;
            } else {
              doc.history.saveCursor -= overflow;
            }
          }
        }

        doc.dirty = doc.history.saveCursor !== doc.history.cursor;
      }
    }),

    cancelMetaTransaction: () => set((state) => {
      if (state.activeDocumentId && state.documents[state.activeDocumentId]) {
        const doc = state.documents[state.activeDocumentId];
        const transaction = doc.history.transaction;
        if (!transaction) {
          throw new Error("Cannot cancel transaction: no active transaction");
        }
        doc.history.transaction = null;
        if (!doc.meta) {
          throw new Error("Cannot cancel transaction: active document has no meta");
        }
        if (transaction.inversePatches.length > 0) {
          doc.meta.data = applyPatches(current(doc.meta.data), transaction.inversePatches) as MetaV2;
        }
        doc.dirty = doc.history.saveCursor !== doc.history.cursor;
      }
    }),
    
    undo: () => set((state) => {
        if (state.activeDocumentId && state.documents[state.activeDocumentId]) {
            const doc = state.documents[state.activeDocumentId];
            if (!doc.meta) {
              return;
            }
            if (doc.history.transaction) {
              throw new Error("Cannot undo while a history transaction is active");
            }
            if (doc.history.cursor > 0) {
                const entry = doc.history.entries[doc.history.cursor - 1];
                doc.meta.data = applyPatches(current(doc.meta.data), entry.inversePatches) as MetaV2;
                doc.history.cursor -= 1;
                doc.dirty = doc.history.saveCursor !== doc.history.cursor;
            }
        }
    }),

    redo: () => set((state) => {
        if (state.activeDocumentId && state.documents[state.activeDocumentId]) {
            const doc = state.documents[state.activeDocumentId];
            if (!doc.meta) {
              return;
            }
            if (doc.history.transaction) {
              throw new Error("Cannot redo while a history transaction is active");
            }
            if (doc.history.cursor < doc.history.entries.length) {
                const entry = doc.history.entries[doc.history.cursor];
                doc.meta.data = applyPatches(current(doc.meta.data), entry.patches) as MetaV2;
                doc.history.cursor += 1;
                doc.dirty = doc.history.saveCursor !== doc.history.cursor;
            }
        }
    }),

    saveActiveDocument: async () => {
      const current = useAppStore.getState();
      if (!current.activeDocumentId || !current.documents[current.activeDocumentId]) return;
      const doc = current.documents[current.activeDocumentId];
      if (!doc.meta) return;
      try {
        await writeText(doc.meta.path, JSON.stringify(doc.meta.data, null, 2));
        await useSymbolIndexStore.getState().patchMetaPath(doc.meta.path);
        // mark as saved in the store
        set((state) => {
          if (state.activeDocumentId && state.documents[state.activeDocumentId]) {
            const doc = state.documents[state.activeDocumentId];
            doc.history.saveCursor = doc.history.cursor;
            doc.dirty = false;
          }
        });
      } catch (e: any) {
        toaster.show({ message: `保存失败: ${e?.message ?? String(e)}`, intent: 'danger' as any });
        throw e;
      }
    },

    saveAllDocuments: async () => {
      const current = useAppStore.getState();
      const dirtyDocuments = Object.values(current.documents).filter((doc) => doc.dirty);
      let savedCount = 0;
      try {
        for (const doc of dirtyDocuments) {
          if (!doc.meta) {
            throw new Error(`Document meta is not loaded: ${doc.id}`);
          }
          await writeText(doc.meta.path, JSON.stringify(doc.meta.data, null, 2));
          await useSymbolIndexStore.getState().patchMetaPath(doc.meta.path);
          set((state) => {
            const target = state.documents[doc.id];
            if (!target) {
              throw new Error(`Document not found: ${doc.id}`);
            }
            target.history.saveCursor = target.history.cursor;
            target.dirty = false;
          });
          savedCount += 1;
        }
        return savedCount;
      } catch (e: any) {
        toaster.show({ message: `保存失败: ${e?.message ?? String(e)}`, intent: 'danger' as any });
        throw e;
      }
    }
  }))
);
