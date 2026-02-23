import { BridgeEnvelope, createBridgeEvent, createBridgeRequest, createBridgeResponse, parseBridgeEnvelope } from "./bridgeProtocol";

/** 事件消息处理器。 */
type BridgeEventHandler = (message: BridgeEnvelope) => void;
type BridgeRequestHandler = (payload: unknown, message: BridgeEnvelope) => unknown | Promise<unknown>;

/** 待完成请求上下文。 */
interface PendingRequest {
  /** 成功回调。 */
  resolve: (value: unknown) => void;
  /** 失败回调。 */
  reject: (reason: unknown) => void;
  /** 超时定时器。 */
  timeout: NodeJS.Timeout;
}

/** VS Code 扩展侧桥接客户端。 */
export class BridgeClient {
  /** iframe 是否已发送 ready 信号。 */
  private ready = false;
  /** ready 前缓存的待发送消息。 */
  private readonly queue: BridgeEnvelope[] = [];
  /** 正在等待响应的请求表。 */
  private readonly pending = new Map<string, PendingRequest>();
  /** 事件订阅处理器表。 */
  private readonly handlers = new Map<string, Set<BridgeEventHandler>>();
  /** 请求处理器表。 */
  private readonly requestHandlers = new Map<string, Set<BridgeRequestHandler>>();

  /** 创建桥接客户端实例。 */
  constructor(private readonly postMessage: (message: unknown) => void) {}

  /** 释放桥接资源并拒绝所有未完成请求。 */
  dispose(): void {
    for (const item of this.pending.values()) {
      clearTimeout(item.timeout);
      item.reject(new Error("Bridge disposed"));
    }
    this.pending.clear();
    this.handlers.clear();
    this.requestHandlers.clear();
    this.queue.length = 0;
  }

  /** 注册事件处理器并返回取消订阅函数。 */
  on(type: string, handler: BridgeEventHandler): () => void {
    let set = this.handlers.get(type);
    if (!set) {
      set = new Set<BridgeEventHandler>();
      this.handlers.set(type, set);
    }
    set.add(handler);
    return () => {
      const current = this.handlers.get(type);
      if (!current) {
        return;
      }
      current.delete(handler);
      if (current.size === 0) {
        this.handlers.delete(type);
      }
    };
  }

  /** 注册请求处理器并返回取消订阅函数。 */
  onRequest(type: string, handler: BridgeRequestHandler): () => void {
    let set = this.requestHandlers.get(type);
    if (!set) {
      set = new Set<BridgeRequestHandler>();
      this.requestHandlers.set(type, set);
    }
    set.add(handler);
    return () => {
      const current = this.requestHandlers.get(type);
      if (!current) {
        return;
      }
      current.delete(handler);
      if (current.size === 0) {
        this.requestHandlers.delete(type);
      }
    };
  }

  /** 处理来自 iframe 的原始消息。 */
  handleIncoming(raw: unknown): void {
    const message = parseBridgeEnvelope(raw);
    if (message.kind === "event" && message.type === "kotonebot.bridge.ready") {
      this.ready = true;
      this.flush();
      return;
    }
    if (message.kind === "response") {
      const requestId = message.requestId;
      if (!requestId) {
        throw new Error("Bridge response missing requestId");
      }
      const pending = this.pending.get(requestId);
      if (!pending) {
        return;
      }
      clearTimeout(pending.timeout);
      this.pending.delete(requestId);
      if (message.ok === false) {
        pending.reject(new Error(message.error || "Bridge request failed"));
      } else {
        pending.resolve(message.payload);
      }
      return;
    }
    if (message.kind === "event") {
      const listeners = this.handlers.get(message.type);
      if (!listeners) {
        return;
      }
      for (const handler of listeners) {
        handler(message);
      }
      return;
    }
    if (message.kind === "request") {
      const listeners = this.requestHandlers.get(message.type);
      if (!listeners || listeners.size === 0) {
        this.dispatch(createBridgeResponse(message.id, message.type, null, false, `No handler registered for ${message.type}`));
        return;
      }
      void (async () => {
        try {
          let value: unknown = null;
          for (const handler of listeners) {
            value = await handler(message.payload, message);
          }
          this.dispatch(createBridgeResponse(message.id, message.type, value, true));
        } catch (err) {
          const text = err instanceof Error ? err.message : String(err);
          this.dispatch(createBridgeResponse(message.id, message.type, null, false, text));
        }
      })();
    }
  }

  /** 发送无需响应的事件消息。 */
  send(type: string, payload: unknown): void {
    const event = createBridgeEvent(type, payload);
    this.dispatch(event);
  }

  /** 发送请求并等待响应。 */
  request(type: string, payload: unknown, timeoutMs = 8000): Promise<unknown> {
    const request = createBridgeRequest(type, payload);
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pending.delete(request.id);
        reject(new Error(`Bridge request timeout: ${type}`));
      }, timeoutMs);
      this.pending.set(request.id, { resolve, reject, timeout });
      this.dispatch(request);
    });
  }

  /** 根据 ready 状态决定直接发送或入队。 */
  private dispatch(message: BridgeEnvelope): void {
    if (!this.ready) {
      this.queue.push(message);
      return;
    }
    this.postMessage(message);
  }

  /** 将缓存队列中的消息顺序发送。 */
  private flush(): void {
    while (this.queue.length > 0) {
      const next = this.queue.shift();
      if (!next) {
        continue;
      }
      this.postMessage(next);
    }
  }
}
