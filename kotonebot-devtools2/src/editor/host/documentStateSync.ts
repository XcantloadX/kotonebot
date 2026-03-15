import { useAppStore } from "../state";
import { emitToHost } from "./hostBridge";

interface EditorDocumentStatePayload {
  metaPath: string;
  content: string;
  dirty: boolean;
}

function buildActiveDocumentSyncPayload(): EditorDocumentStatePayload | null {
  const state = useAppStore.getState();
  const activeId = state.activeDocumentId;
  if (!activeId) {
    return null;
  }
  const activeDoc = state.documents[activeId];
  if (!activeDoc || !activeDoc.meta) {
    return null;
  }
  return {
    metaPath: activeDoc.meta.path,
    content: JSON.stringify(activeDoc.meta.data, null, 2),
    dirty: activeDoc.dirty,
  };
}

export function installDocumentStateSync(): () => void {
  let lastSerialized = "";

  const push = () => {
    const payload = buildActiveDocumentSyncPayload();
    if (!payload) {
      return;
    }
    const serialized = JSON.stringify(payload);
    if (serialized === lastSerialized) {
      return;
    }
    lastSerialized = serialized;
    emitToHost("kotonebot.editor.documentState", payload);
  };

  push();
  const unsubscribe = useAppStore.subscribe(() => {
    push();
  });

  return () => {
    unsubscribe();
  };
}
