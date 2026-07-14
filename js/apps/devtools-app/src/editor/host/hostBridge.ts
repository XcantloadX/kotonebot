import { BridgeEnvelope, createIframeEvent, createIframeRequest, createIframeResponse, parseBridgeEnvelope } from "./bridgeProtocol";

type HostHandler = (payload: unknown, message: BridgeEnvelope) => unknown | Promise<unknown>;

const handlers = new Map<string, Set<HostHandler>>();
const pendingRequests = new Map<string, { resolve: (value: unknown) => void; reject: (reason: unknown) => void; timeout: number }>();

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function readSingleTabModeFromQuery(): boolean {
  const value = new URLSearchParams(window.location.search).get("singleTabMode");
  if (value === null) {
    return false;
  }
  const normalized = value.trim().toLowerCase();
  return normalized === "1" || normalized === "true";
}

function postToHost(message: BridgeEnvelope): void {
  window.parent.postMessage(message, "*");
}

function notifyError(type: string, error: unknown): void {
  const text = error instanceof Error ? error.message : String(error);
  postToHost(createIframeEvent("kotonebot.bridge.error", { type, message: text }));
}

export function emitToHost(type: string, payload: unknown): void {
  postToHost(createIframeEvent(type, payload));
}

export function isHostMode(): boolean {
  return window.parent !== window;
}

export function isSingleTabMode(): boolean {
  return readSingleTabModeFromQuery();
}

export function shouldUseSingleTabHostOpen(): boolean {
  return isHostMode() && isSingleTabMode();
}

export function requestHost(type: string, payload: unknown, timeoutMs = 8000): Promise<unknown> {
  const request = createIframeRequest(type, payload);
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      pendingRequests.delete(request.id);
      reject(new Error(`Host request timeout: ${type}`));
    }, timeoutMs);
    pendingRequests.set(request.id, { resolve, reject, timeout });
    postToHost(request);
  });
}

export function registerHostMessage(type: string, handler: HostHandler): () => void {
  let set = handlers.get(type);
  if (!set) {
    set = new Set<HostHandler>();
    handlers.set(type, set);
  }
  set.add(handler);
  return () => {
    const current = handlers.get(type);
    if (!current) {
      return;
    }
    current.delete(handler);
    if (current.size === 0) {
      handlers.delete(type);
    }
  };
}

async function dispatchMessage(message: BridgeEnvelope): Promise<void> {
  const set = handlers.get(message.type);
  if (!set || set.size === 0) {
    if (message.kind === "request") {
      postToHost(
        createIframeResponse(message.id, message.type, null, false, `No handler registered for ${message.type}`),
      );
    }
    return;
  }
  if (message.kind === "event") {
    for (const handler of set) {
      await handler(message.payload, message);
    }
    return;
  }
  if (message.kind === "request") {
    try {
      let value: unknown = null;
      for (const handler of set) {
        value = await handler(message.payload, message);
      }
      postToHost(createIframeResponse(message.id, message.type, value, true));
    } catch (err) {
      const text = err instanceof Error ? err.message : String(err);
      postToHost(createIframeResponse(message.id, message.type, null, false, text));
    }
  }
}

export function installHostBridge(): () => void {
  const onMessage = (event: MessageEvent) => {
    if (event.source === window) {
      return;
    }
    let message: BridgeEnvelope;
    try {
      message = parseBridgeEnvelope(event.data);
    } catch (err) {
      notifyError("parse", err);
      return;
    }
    if (message.source !== "extension") {
      return;
    }
    if (message.kind === "response") {
      const requestId = message.requestId;
      if (typeof requestId !== "string" || requestId.trim() === "") {
        notifyError("response", new Error("Host response missing requestId"));
        return;
      }
      const pending = pendingRequests.get(requestId);
      if (!pending) {
        return;
      }
      window.clearTimeout(pending.timeout);
      pendingRequests.delete(requestId);
      if (message.ok === false) {
        pending.reject(new Error(message.error || "Host request failed"));
      } else {
        pending.resolve(message.payload);
      }
      return;
    }
    void dispatchMessage(message).catch((err) => {
      notifyError(message.type, err);
    });
  };
  window.addEventListener("message", onMessage);
  emitToHost("kotonebot.bridge.ready", { capabilities: Array.from(handlers.keys()) });
  return () => {
    window.removeEventListener("message", onMessage);
    for (const [id, pending] of pendingRequests.entries()) {
      window.clearTimeout(pending.timeout);
      pendingRequests.delete(id);
      pending.reject(new Error("Host bridge disposed"));
    }
  };
}
