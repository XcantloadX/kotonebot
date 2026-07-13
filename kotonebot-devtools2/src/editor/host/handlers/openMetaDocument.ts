import { editorActions } from "../../actions";
import { registerHostMessage } from "../hostBridge";

interface OpenMetaDocumentPayload {
  metaPath: string;
  imagePath: string;
}

import { normalizePath } from "../../../shared/normalizePath";

function parsePayload(value: unknown): OpenMetaDocumentPayload {
  if (typeof value !== "object" || value === null) {
    throw new Error("kotonebot.openMetaDocument payload is required");
  }
  const payload = value as Partial<OpenMetaDocumentPayload>;
  if (typeof payload.metaPath !== "string" || payload.metaPath.trim() === "") {
    throw new Error("kotonebot.openMetaDocument payload.metaPath is required");
  }
  if (!payload.metaPath.toLowerCase().endsWith(".png.json")) {
    throw new Error(`kotonebot.openMetaDocument payload.metaPath must end with .png.json: ${payload.metaPath}`);
  }
  if (typeof payload.imagePath !== "string" || payload.imagePath.trim() === "") {
    throw new Error("kotonebot.openMetaDocument payload.imagePath is required");
  }
  if (!payload.imagePath.toLowerCase().endsWith(".png")) {
    throw new Error(`kotonebot.openMetaDocument payload.imagePath must end with .png: ${payload.imagePath}`);
  }
  const expectedMetaPath = `${payload.imagePath}.json`;
  if (normalizePath(payload.metaPath) !== normalizePath(expectedMetaPath)) {
    throw new Error(
      `kotonebot.openMetaDocument payload mismatch: metaPath=${payload.metaPath}, imagePath=${payload.imagePath}`,
    );
  }
  return payload as OpenMetaDocumentPayload;
}

export function registerOpenMetaDocumentHandler(): () => void {
  return registerHostMessage("kotonebot.openMetaDocument", async (payload) => {
    const parsed = parsePayload(payload);
    await editorActions.image.openWithMeta(parsed.imagePath, { allowHostDelegate: false, source: "host" });
    return { ok: true };
  });
}
