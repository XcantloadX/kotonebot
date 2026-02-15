import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { current } from 'immer';
import { MetaV2, ResourceType } from '../model/metaV2';
import { PrefabSchema } from '../model/prefabSchema';
import { writeText } from '../api/fs';
import { toaster } from '../ui/toaster';
import { useSymbolIndexStore } from './symbolIndexStore';

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
    past: MetaV2[];
    future: MetaV2[];
  };
  
  view?: { x: number; y: number; scale: number };
}

interface AppState {
  documents: Record<string, DocumentState>;
  activeDocumentId: string | null;
  
  prefabSchema: PrefabSchema | null;
  activeTool: ToolType;
  activeResourceType: ResourceType;

  // Actions
  openDocument: (path: string, width: number, height: number) => void;
  closeDocument: (id: string) => void;
  setActiveDocument: (id: string) => void;
  setViewState: (id: string, view: { x: number; y: number; scale: number }) => void;
  
  setPrefabSchema: (schema: PrefabSchema) => void;
  setActiveTool: (tool: ToolType) => void;
  setActiveResourceType: (type: ResourceType) => void;

  // Active Document Actions
  setSelection: (definitionId: string | null) => void;
  setMode: (mode: InteractionMode) => void;
  setActiveMeta: (docId: string, data: MetaV2) => void;
  updateMeta: (updater: (draft: MetaV2) => void) => void;
  
  undo: () => void;
  redo: () => void;
  saveActiveDocument: () => Promise<void>;
}

export const useAppStore = create<AppState>()(
  immer((set) => ({
    documents: {},
    activeDocumentId: null,
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
        history: { past: [], future: [] }
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
           doc.history = { past: [], future: [] };
       }
    }),

    updateMeta: (updater) => set((state) => {
      if (state.activeDocumentId && state.documents[state.activeDocumentId]) {
        const doc = state.documents[state.activeDocumentId];
        if (doc.meta) {
            // Push current state to past
            doc.history.past.push(current(doc.meta.data));
            doc.history.future = [];
            
            // Apply updates
            updater(doc.meta.data);
            doc.dirty = true;
        }
      }
    }),
    
    undo: () => set((state) => {
        if (state.activeDocumentId && state.documents[state.activeDocumentId]) {
            const doc = state.documents[state.activeDocumentId];
            if (doc.history.past.length > 0) {
                const previous = doc.history.past.pop();
                if (doc.meta && previous) {
                    doc.history.future.push(current(doc.meta.data));
                    doc.meta.data = previous;
                    doc.dirty = true; 
                }
            }
        }
    }),

    redo: () => set((state) => {
        if (state.activeDocumentId && state.documents[state.activeDocumentId]) {
            const doc = state.documents[state.activeDocumentId];
            if (doc.history.future.length > 0) {
                const next = doc.history.future.pop();
                if (doc.meta && next) {
                    doc.history.past.push(current(doc.meta.data));
                    doc.meta.data = next;
                    doc.dirty = true;
                }
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
            state.documents[state.activeDocumentId].dirty = false;
          }
        });
      } catch (e: any) {
        toaster.show({ message: `保存失败: ${e?.message ?? String(e)}`, intent: 'danger' as any });
        throw e;
      }
    }
  }))
);
