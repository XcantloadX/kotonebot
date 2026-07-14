import { useAppStore } from "../../state";
import { getActiveDocumentId } from "../../commands/selectors";
import { registerHostMessage } from "../hostBridge";

interface RunEditorCommandPayload {
  command: "undo" | "redo" | "save";
}

function parsePayload(value: unknown): RunEditorCommandPayload {
  if (typeof value !== "object" || value === null) {
    throw new Error("kotonebot.editor.runCommand payload is required");
  }
  const payload = value as Partial<RunEditorCommandPayload>;
  if (payload.command !== "undo" && payload.command !== "redo" && payload.command !== "save") {
    throw new Error(`kotonebot.editor.runCommand payload.command is invalid: ${String(payload.command)}`);
  }
  return payload as RunEditorCommandPayload;
}

export function registerRunEditorCommandHandler(): () => void {
  return registerHostMessage("kotonebot.editor.runCommand", async (payload) => {
    const parsed = parsePayload(payload);
    const store = useAppStore.getState();
    const docId = getActiveDocumentId();
    if (!docId) return { ok: false };
    switch (parsed.command) {
      case "undo":
        store.undo(docId);
        return { ok: true };
      case "redo":
        store.redo(docId);
        return { ok: true };
      case "save":
        await store.saveDocument(docId);
        return { ok: true };
      default:
        throw new Error(`Unsupported run command: ${String(parsed.command)}`);
    }
  });
}
