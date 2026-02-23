export const BRIDGE_PROTOCOL_VERSION = 1 as const;

export type BridgeKind = "event" | "request" | "response";
export type BridgeSource = "extension" | "iframe";

export interface BridgeEnvelope {
  version: number;
  id: string;
  kind: BridgeKind;
  type: string;
  source: BridgeSource;
  ts: number;
  payload: unknown;
  requestId?: string;
  ok?: boolean;
  error?: string;
}

function nextId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

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

export function createIframeEvent(type: string, payload: unknown): BridgeEnvelope {
  return {
    version: BRIDGE_PROTOCOL_VERSION,
    id: nextId(),
    kind: "event",
    type,
    source: "iframe",
    ts: Date.now(),
    payload,
  };
}

export function createIframeResponse(
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
    source: "iframe",
    ts: Date.now(),
    payload,
    requestId,
    ok,
    error,
  };
}
