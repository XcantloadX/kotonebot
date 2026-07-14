import { messageBox } from "../../ui/messageBox";
import { useAppStore } from "../state";
import { getActiveDocumentId } from "../commands/selectors";
import i18n from "../../i18n";

export async function closeDocumentWithChecks(id: string): Promise<boolean> {
  const current = useAppStore.getState();
  const doc = current.documents[id];
  if (!doc) {
    throw new Error(`Document not found: ${id}`);
  }
  if (!doc.dirty) {
    current.closeTab(id);
    current.removeDocument(id);
    return true;
  }

  const action = await messageBox.show<"save" | "dont-save" | "cancel">({
    title: i18n.t('document.unsavedChanges'),
    content: i18n.t('document.saveChangesPrompt', { fileName: id.split("/").pop() }),
    buttons: [
      { value: "save", text: i18n.t('menuItem.save'), intent: "primary" },
      { value: "dont-save", text: i18n.t('document.dontSave') },
      { value: "cancel", text: i18n.t('dialog.cancel') },
    ],
    dismissValue: "cancel",
    canEscapeKeyClose: true,
    canOutsideClickClose: false,
  });

  if (action === "cancel") {
    return false;
  }
  if (action === "save") {
    current.setActiveTab(id);
    try {
      await current.saveDocument(id);
    } catch {
      return false;
    }
  }
  current.closeTab(id);
  current.removeDocument(id);
  return true;
}

export async function closeDocumentsWithChecks(ids: string[]): Promise<boolean> {
  for (const id of ids) {
    const ok = await closeDocumentWithChecks(id);
    if (!ok) {
      return false;
    }
  }
  return true;
}

export async function closeActiveDocumentWithChecks(): Promise<boolean> {
  const activeId = getActiveDocumentId();
  if (!activeId) {
    throw new Error("No active document");
  }
  return closeDocumentWithChecks(activeId);
}

export async function closeAllDocumentsWithChecks(): Promise<boolean> {
  const ids = Object.keys(useAppStore.getState().documents);
  return closeDocumentsWithChecks(ids);
}
