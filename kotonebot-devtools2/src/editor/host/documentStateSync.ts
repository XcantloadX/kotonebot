import { useAppStore } from "../state";
import { selectActiveDocumentId } from "../commands/selectors";
import { emitToHost } from "./hostBridge";

interface EditorDocumentStatePayload {
  metaPath: string;
  content: string;
  dirty: boolean;
}

export function installDocumentStateSync(): () => void {
  let lastSerialized: string | null = null;

  const push = () => {
    const state = useAppStore.getState();
    const activeId = selectActiveDocumentId(state);
    if (!activeId) return;
    const activeDoc = state.documents[activeId];
    if (!activeDoc || !activeDoc.meta) return;

    const payload = {
      metaPath: activeDoc.meta.path,
      content: JSON.stringify(activeDoc.meta.data, null, 2),
      dirty: activeDoc.dirty,
    };
    const serialized = JSON.stringify(payload);
    if (serialized !== lastSerialized) {
      lastSerialized = serialized;
      emitToHost("kotonebot.editor.documentState", payload);
    }
  };

  push();

  let lastMetaRef: unknown = null;
  let lastMetaPath: string | null = null;
  let lastDirty: boolean | null = null;

  const unsubscribe = useAppStore.subscribe((state) => {
    const activeId = selectActiveDocumentId(state);
    if (!activeId) return;
    const activeDoc = state.documents[activeId];
    if (!activeDoc || !activeDoc.meta) return;

    const dirty = activeDoc.dirty;
    if (activeDoc.meta.path !== lastMetaPath || dirty !== lastDirty) {
      lastMetaPath = activeDoc.meta.path;
      lastDirty = dirty;
      push();
      return;
    }

    if (activeDoc.meta.data !== lastMetaRef) {
      lastMetaRef = activeDoc.meta.data;
      push();
    }
  });

  return () => {
    unsubscribe();
  };
}
