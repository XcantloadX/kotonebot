import { MessageBoxApi } from "../../ui/messageBox";
import { useAppStore } from "../state";

export async function closeDocumentWithChecks(messageBox: MessageBoxApi, id: string): Promise<boolean> {
  const current = useAppStore.getState();
  const doc = current.documents[id];
  if (!doc) {
    throw new Error(`Document not found: ${id}`);
  }
  if (!doc.dirty) {
    current.closeDocument(id);
    return true;
  }

  const action = await messageBox.show<"save" | "dont-save" | "cancel">({
    title: "Unsaved changes",
    content: `File "${id.split(/[/\\]/).pop()}" has unsaved changes. Save before closing?`,
    buttons: [
      { value: "save", text: "Save", intent: "primary" },
      { value: "dont-save", text: "Don't Save" },
      { value: "cancel", text: "Cancel" },
    ],
    dismissValue: "cancel",
    canEscapeKeyClose: true,
    canOutsideClickClose: false,
  });

  if (action === "cancel") {
    return false;
  }
  if (action === "save") {
    current.setActiveDocument(id);
    try {
      await current.saveActiveDocument();
    } catch {
      return false;
    }
  }
  current.closeDocument(id);
  return true;
}

export async function closeDocumentsWithChecks(messageBox: MessageBoxApi, ids: string[]): Promise<boolean> {
  for (const id of ids) {
    const ok = await closeDocumentWithChecks(messageBox, id);
    if (!ok) {
      return false;
    }
  }
  return true;
}

export async function closeActiveDocumentWithChecks(messageBox: MessageBoxApi): Promise<boolean> {
  const current = useAppStore.getState();
  const activeId = current.activeDocumentId;
  if (!activeId) {
    throw new Error("No active document");
  }
  return closeDocumentWithChecks(messageBox, activeId);
}

export async function closeAllDocumentsWithChecks(messageBox: MessageBoxApi): Promise<boolean> {
  const ids = Object.keys(useAppStore.getState().documents);
  return closeDocumentsWithChecks(messageBox, ids);
}
