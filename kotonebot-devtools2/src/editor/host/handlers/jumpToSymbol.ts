import { editorActions } from "../../actions";
import { registerHostMessage } from "../hostBridge";
import { useSymbolIndexStore } from "../../symbolIndexStore";

interface JumpToSymbolPayload {
  metaPath: string;
  imagePath: string;
  definitionId: string;
}

function normalizePath(path: string): string {
  return path.replace(/\\/g, "/").toLowerCase();
}

function parsePayload(value: unknown): JumpToSymbolPayload {
  if (typeof value !== "object" || value === null) {
    throw new Error("kotonebot.jumpToSymbol payload is required");
  }
  const payload = value as Partial<JumpToSymbolPayload>;
  if (typeof payload.metaPath !== "string" || payload.metaPath.trim() === "") {
    throw new Error("kotonebot.jumpToSymbol payload.metaPath is required");
  }
  if (typeof payload.imagePath !== "string" || payload.imagePath.trim() === "") {
    throw new Error("kotonebot.jumpToSymbol payload.imagePath is required");
  }
  if (typeof payload.definitionId !== "string" || payload.definitionId.trim() === "") {
    throw new Error("kotonebot.jumpToSymbol payload.definitionId is required");
  }
  return payload as JumpToSymbolPayload;
}

export function registerJumpToSymbolHandler(): () => void {
  return registerHostMessage("kotonebot.jumpToSymbol", async (payload) => {
    const parsed = parsePayload(payload);
    const store = useSymbolIndexStore.getState();
    if (!store.initialized) {
      await store.initialize();
    }
    const normalizedMetaPath = normalizePath(parsed.metaPath);
    const symbol = useSymbolIndexStore.getState().symbols.find((item) => {
      return normalizePath(item.metaPath) === normalizedMetaPath && item.definitionId === parsed.definitionId;
    });
    if (!symbol) {
      throw new Error(`Symbol not found: ${parsed.metaPath}::${parsed.definitionId}`);
    }
    await editorActions.navigation.jumpToSymbol(symbol);
    return { ok: true };
  });
}
