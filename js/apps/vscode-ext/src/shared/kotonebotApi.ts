import { DevtoolsHttpConfig } from "../lsp/client";
import { requestBuffer, requestJsonUnknown } from "./http";

/** Meta 索引中的轻量符号条目。 */
export interface SymbolLite {
  /** 唯一符号键。 */
  symbolKey: string;
  /** definition 标识。 */
  definitionId: string;
  /** definition 类型。 */
  type: string;
  /** 符号全名。 */
  name: string;
  /** 可读名称。 */
  displayName: string | null;
  /** 描述。 */
  description: string | null;
  /** prefab 标识。 */
  prefabId: string | null;
  /** 变体名称。 */
  variant: string | null;
  /** meta 文件路径。 */
  metaPath: string;
  /** 图片文件路径。 */
  imagePath: string;
  /** 主要几何信息。 */
  primaryGeometry: Record<string, unknown> | null;
}

/** Meta 索引快照。 */
export interface SymbolSnapshotLite {
  /** 索引版本。 */
  indexVersion: number;
  /** 内容哈希。 */
  contentHash: string;
  /** 符号列表。 */
  symbols: SymbolLite[];
}

/** 判断值是否为对象。 */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** 读取对象字段并保证存在。 */
function requireField(record: Record<string, unknown>, key: string): unknown {
  if (!(key in record)) {
    throw new Error(`Missing field: ${key}`);
  }
  return record[key];
}

/** 读取字符串字段。 */
function requireString(record: Record<string, unknown>, key: string): string {
  const value = requireField(record, key);
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`Invalid string field: ${key}`);
  }
  return value;
}

/** 读取可空字符串字段。 */
function requireNullableString(record: Record<string, unknown>, key: string): string | null {
  const value = requireField(record, key);
  if (value === null) {
    return null;
  }
  if (typeof value !== "string") {
    throw new Error(`Invalid nullable string field: ${key}`);
  }
  return value;
}

/** 读取整数数字字段。 */
function requireNumber(record: Record<string, unknown>, key: string): number {
  const value = requireField(record, key);
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`Invalid number field: ${key}`);
  }
  return value;
}

/** 解析通用 API Envelope。 */
function parseEnvelope(raw: unknown): { success: boolean; message: string | null; data: unknown } {
  if (!isRecord(raw)) {
    throw new Error("API response must be object");
  }
  const successRaw = requireField(raw, "success");
  if (typeof successRaw !== "boolean") {
    throw new Error("Invalid envelope.success");
  }
  const messageRaw = requireField(raw, "message");
  if (messageRaw !== null && typeof messageRaw !== "string") {
    throw new Error("Invalid envelope.message");
  }
  const data = requireField(raw, "data");
  return { success: successRaw, message: messageRaw, data };
}

/** 请求并解析 API Envelope 数据。 */
async function fetchEnvelopeData(url: string, errorPrefix: string): Promise<unknown> {
  const raw = await requestJsonUnknown(url);
  const envelope = parseEnvelope(raw);
  if (envelope.success !== true) {
    throw new Error(`${errorPrefix}: ${String(envelope.message)}`);
  }
  if (envelope.data === null) {
    throw new Error(`${errorPrefix}: data is null`);
  }
  return envelope.data;
}

/** 解析项目根中的编辑器配置并返回 r_file。 */
function parseEditorRFile(data: unknown): string {
  if (!isRecord(data)) {
    throw new Error("project root response data is invalid");
  }
  const editor = requireField(data, "editor");
  if (!isRecord(editor)) {
    throw new Error("project root response editor is null");
  }
  const rFile = requireField(editor, "r_file");
  if (typeof rFile !== "string" || rFile.trim() === "") {
    throw new Error("Missing [tool.kotonebot.editor.r_file] in pyproject.toml");
  }
  return rFile;
}

/** 解析项目根中的 base variant。 */
function parseBaseVariant(data: unknown): string {
  if (!isRecord(data)) {
    throw new Error("project root response data is invalid");
  }
  const variant = requireField(data, "variant");
  if (!isRecord(variant)) {
    throw new Error("project root response variant is null");
  }
  const base = requireField(variant, "base");
  if (typeof base !== "string" || base.trim() === "") {
    throw new Error("project root response variant.base is invalid");
  }
  return base;
}

/** 解析单个 SymbolLite。 */
function parseSymbolLite(raw: unknown): SymbolLite {
  if (!isRecord(raw)) {
    throw new Error("meta index symbol item must be object");
  }
  const primaryGeometryRaw = requireField(raw, "primaryGeometry");
  if (primaryGeometryRaw !== null && !isRecord(primaryGeometryRaw)) {
    throw new Error("meta index symbol.primaryGeometry is invalid");
  }
  return {
    symbolKey: requireString(raw, "symbolKey"),
    definitionId: requireString(raw, "definitionId"),
    type: requireString(raw, "type"),
    name: requireString(raw, "name"),
    displayName: requireNullableString(raw, "displayName"),
    description: requireNullableString(raw, "description"),
    prefabId: requireNullableString(raw, "prefabId"),
    variant: requireNullableString(raw, "variant"),
    metaPath: requireString(raw, "metaPath"),
    imagePath: requireString(raw, "imagePath"),
    primaryGeometry: primaryGeometryRaw as Record<string, unknown> | null,
  };
}

/** 解析 Meta 索引快照。 */
function parseSymbolSnapshot(data: unknown): SymbolSnapshotLite {
  if (!isRecord(data)) {
    throw new Error("meta index response data is invalid");
  }
  const symbolsRaw = requireField(data, "symbols");
  if (!Array.isArray(symbolsRaw)) {
    throw new Error("meta index response symbols is invalid");
  }
  return {
    indexVersion: requireNumber(data, "indexVersion"),
    contentHash: requireString(data, "contentHash"),
    symbols: symbolsRaw.map((item) => parseSymbolLite(item)),
  };
}

/** 读取项目根配置中的 r_file。 */
export async function fetchProjectEditorRFile(server: DevtoolsHttpConfig): Promise<string> {
  const data = await fetchEnvelopeData(
    `http://${server.host}:${String(server.port)}/api/project/root`,
    "project root request failed",
  );
  return parseEditorRFile(data);
}

/** 读取项目根配置中的 base variant 名称。 */
export async function fetchProjectBaseVariant(server: DevtoolsHttpConfig): Promise<string> {
  const data = await fetchEnvelopeData(
    `http://${server.host}:${String(server.port)}/api/project/root`,
    "project root request failed",
  );
  return parseBaseVariant(data);
}

/** 拉取 Meta 索引快照。 */
export async function fetchMetaIndexSnapshot(server: DevtoolsHttpConfig): Promise<SymbolSnapshotLite> {
  const data = await fetchEnvelopeData(
    `http://${server.host}:${String(server.port)}/api/meta/index`,
    "meta index request failed",
  );
  return parseSymbolSnapshot(data);
}

/** 拉取 hover 预览图。 */
export async function fetchHoverPreviewImage(
  server: DevtoolsHttpConfig,
  imagePath: string,
  primaryGeometry: Record<string, unknown> | null,
): Promise<Buffer> {
  const params = new URLSearchParams();
  params.set("path", imagePath);
  if (primaryGeometry !== null) {
    const kind = primaryGeometry.kind;
    if (kind === "image" || kind === "rect") {
      for (const key of ["x1", "y1", "x2", "y2"]) {
        const value = primaryGeometry[key];
        if (value === undefined || value === null) {
          throw new Error(`primaryGeometry missing ${key}`);
        }
        params.set(key, String(value));
      }
    }
  }
  const url = `http://${server.host}:${String(server.port)}/api/image/hover_preview?${params.toString()}`;
  return requestBuffer(url);
}
