import { useAppStore } from "../state";
import { toaster } from "../../ui/toaster";

export async function saveActiveDocumentWithToast(): Promise<void> {
  try {
    await useAppStore.getState().saveActiveDocument();
    toaster.show({ message: "Saved", intent: "success" });
  } catch {
    toaster.show({ message: "Failed to save", intent: "danger" });
  }
}
