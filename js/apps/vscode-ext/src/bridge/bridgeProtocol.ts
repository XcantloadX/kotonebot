/** 扩展与内嵌页面通信协议版本号。 */
export const BRIDGE_PROTOCOL_VERSION = 1 as const;

/** 通信消息类别。 */
export type BridgeKind = "event" | "request" | "response";
/** 通信消息来源。 */
export type BridgeSource = "extension" | "iframe";

/** 桥接层统一消息包结构。 */
export interface BridgeEnvelope {
  /** 协议版本。 */
  version: number;
  /** 当前消息唯一标识。 */
  id: string;
  /** 消息类别。 */
  kind: BridgeKind;
  /** 业务消息类型。 */
  type: string;
  /** 消息来源。 */
  source: BridgeSource;
  /** 发送时间戳（毫秒）。 */
  ts: number;
  /** 业务负载。 */
  payload: unknown;
  /** 响应消息关联的请求 ID。 */
  requestId?: string;
  /** 请求是否执行成功。 */
  ok?: boolean;
  /** 失败时的错误信息。 */
  error?: string;
}

/** 生成桥接消息 ID。 */
function nextId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

/** 判断值是否为对象字典。 */
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** 解析并校验桥接消息。 */
export function parseBridgeEnvelope(value: unknown): BridgeEnvelope {
  if (!isRecord(value)) {
    throw new Error("Bridge message must be an object");
  }
  const version = value.version;
  const id = value.id;
  const kind = value.kind;
  const type = value.type;
  const source = value.source;
  const ts = value.ts;
  if (version !== BRIDGE_PROTOCOL_VERSION) {
    throw new Error(`Unsupported bridge protocol version: ${String(version)}`);
  }
  if (typeof id !== "string" || id.trim() === "") {
    throw new Error("Bridge message id is required");
  }
  if (kind !== "event" && kind !== "request" && kind !== "response") {
    throw new Error(`Unsupported bridge message kind: ${String(kind)}`);
  }
  if (typeof type !== "string" || type.trim() === "") {
    throw new Error("Bridge message type is required");
  }
  if (source !== "extension" && source !== "iframe") {
    throw new Error(`Unsupported bridge source: ${String(source)}`);
  }
  if (typeof ts !== "number" || !Number.isFinite(ts)) {
    throw new Error("Bridge message timestamp is invalid");
  }
  const envelope: BridgeEnvelope = {
    version,
    id,
    kind,
    type,
    source,
    ts,
    payload: value.payload,
  };
  if (value.requestId !== undefined) {
    if (typeof value.requestId !== "string" || value.requestId.trim() === "") {
      throw new Error("Bridge response requestId is invalid");
    }
    envelope.requestId = value.requestId;
  }
  if (value.ok !== undefined) {
    if (typeof value.ok !== "boolean") {
      throw new Error("Bridge response ok flag is invalid");
    }
    envelope.ok = value.ok;
  }
  if (value.error !== undefined) {
    if (typeof value.error !== "string" || value.error.trim() === "") {
      throw new Error("Bridge response error is invalid");
    }
    envelope.error = value.error;
  }
  return envelope;
}

/** 创建扩展侧事件消息。 */
export function createBridgeEvent(type: string, payload: unknown): BridgeEnvelope {
  return {
    version: BRIDGE_PROTOCOL_VERSION,
    id: nextId(),
    kind: "event",
    type,
    source: "extension",
    ts: Date.now(),
    payload,
  };
}

/** 创建扩展侧请求消息。 */
export function createBridgeRequest(type: string, payload: unknown): BridgeEnvelope {
  return {
    version: BRIDGE_PROTOCOL_VERSION,
    id: nextId(),
    kind: "request",
    type,
    source: "extension",
    ts: Date.now(),
    payload,
  };
}

/** 创建扩展侧响应消息。 */
export function createBridgeResponse(
  requestId: string,
  type: string,
  payload: unknown,
  ok: boolean,
  error?: string,
): BridgeEnvelope {
  return {
    version: BRIDGE_PROTOCOL_VERSION,
    id: nextId(),
    kind: "response",
    type,
    source: "extension",
    ts: Date.now(),
    payload,
    requestId,
    ok,
    error,
  };
}
