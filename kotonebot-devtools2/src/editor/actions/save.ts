import { useAppStore } from "../state";
import { toaster } from "../../ui/toaster";
import i18n from "../../i18n";

export async function saveActiveDocumentWithToast(): Promise<void> {
  try {
    await useAppStore.getState().saveActiveDocument();
    toaster.show({ message: i18n.t('status.saved'), intent: "success" });
  } catch {
    toaster.show({ message: i18n.t('error.saveFailed', { message: '' }), intent: "danger" });
  }
}

export async function saveAllDocumentsWithToast(): Promise<void> {
  try {
    const savedCount = await useAppStore.getState().saveAllDocuments();
    toaster.show({ message: i18n.t('status.saved') + ` ${savedCount} files`, intent: "success" });
  } catch {
    toaster.show({ message: i18n.t('error.saveFailed', { message: '' }), intent: "danger" });
  }
}
