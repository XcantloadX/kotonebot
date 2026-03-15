import { useAppStore } from "../../state";
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
    switch (parsed.command) {
      case "undo":
        store.undo();
        return { ok: true };
      case "redo":
        store.redo();
        return { ok: true };
      case "save":
        await store.saveActiveDocument();
        return { ok: true };
      default:
        throw new Error(`Unsupported run command: ${String(parsed.command)}`);
    }
  });
}
