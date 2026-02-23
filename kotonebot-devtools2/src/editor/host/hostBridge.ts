import { BridgeEnvelope, createIframeEvent, createIframeResponse, parseBridgeEnvelope } from "./bridgeProtocol";

type HostHandler = (payload: unknown, message: BridgeEnvelope) => unknown | Promise<unknown>;

const handlers = new Map<string, Set<HostHandler>>();

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
    void dispatchMessage(message).catch((err) => {
      notifyError(message.type, err);
    });
  };
  window.addEventListener("message", onMessage);
  emitToHost("kotonebot.bridge.ready", { capabilities: Array.from(handlers.keys()) });
  return () => {
    window.removeEventListener("message", onMessage);
  };
}
