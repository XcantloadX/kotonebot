export type ImageSource = {
  type: 'memory';
  value: string[];
};

/**
 * 表示可视化事件的数据结构
 */
export type VisualEventData = {
  /** 图片数据源 */
  image: ImageSource;
  /** 函数或操作的名称 */
  name: string;
  /** 详细的文本信息 */
  details: string;
};

/**
 * 可视化事件的完整结构
 */
export type VisualEvent = {
  type: 'visual';
  data: VisualEventData;
};

/**
 * WebSocket 连接状态事件
 */
export type ConnectionStatusEvent = {
  type: 'connectionStatus';
  /** 连接状态：true 表示已连接，false 表示已断开 */
  connected: boolean;
};

/** 支持的事件类型 */
export type KotoneDebugEvents = 'visual' | 'connectionStatus';

/**
 * 事件类型到事件数据的映射类型
 */
type EventTypeMap<T extends KotoneDebugEvents> = T extends 'visual' 
  ? VisualEvent 
  : T extends 'connectionStatus' 
  ? ConnectionStatusEvent 
  : never;

/**
 * 事件监听器映射类型
 */
type EventListenerMap = {
  visual: Array<(data: VisualEvent) => void>;
  connectionStatus: Array<(data: ConnectionStatusEvent) => void>;
};

export type RunCodeResultSuccess = {
  status: 'ok';
  result: any;
};

export type RunCodeResultError = {
  status: 'error';
  message: string;
  traceback: string;
};


/**
 * Kotone 调试客户端类
 * 用于处理与调试服务器的 WebSocket 通信
 */
export class KotoneDebugClient {
  /** WebSocket 实例 */
  #ws: WebSocket | null = null;
  /** 事件监听器映射 */
  #eventListeners: EventListenerMap = {
    visual: [],
    connectionStatus: []
  };
  /** 是否正在重连 */
  #isReconnecting: boolean;
  /** WebSocket 服务器 URL */
  #serverUrl: string;
  /** 服务器地址 */
  host: string;


  /**
   * 创建一个新的 Kotone 调试客户端实例
   * @param host - WebSocket 服务器的 IP 地址
   */
  constructor(host: string) {
    this.host = host;
    this.#serverUrl = `ws://${host}/ws`;
    this.#isReconnecting = false;
    this.#connect();
  }

  /**
   * 添加事件监听器
   * @param event - 要监听的事件类型
   * @param callback - 事件回调函数
   */
  addEventListener<T extends KotoneDebugEvents>(
    event: T, 
    callback: (e: EventTypeMap<T>) => void
  ): void {
    (this.#eventListeners[event] as Array<(data: EventTypeMap<T>) => void>).push(callback);
  }

  /**
   * 移除事件监听器
   * @param event - 要移除监听器的事件类型
   * @param callback - 要移除的回调函数
   */
  removeEventListener<T extends KotoneDebugEvents>(
    event: T, 
    callback: (e: EventTypeMap<T>) => void
  ): void {
    const listeners = this.#eventListeners[event] as Array<(data: EventTypeMap<T>) => void>;
    const index = listeners.indexOf(callback);
    if (index !== -1) {
      listeners.splice(index, 1);
    }
  }

  /**
   * 建立 WebSocket 连接
   * @private
   */
  #connect(): void {
    if (this.#isReconnecting) return;
    this.#isReconnecting = true;

    try {
      this.#ws = new WebSocket(this.#serverUrl);
    } catch (error) {
      console.log(error);
      this.#checkServerStatus();
      return;
    }
    
    this.#ws.onopen = () => {
      console.log('WebSocket connected');
      this.#isReconnecting = false;
      this.#dispatchEvent('connectionStatus', { type: 'connectionStatus', connected: true });
    };
    
    this.#ws.onmessage = (event: MessageEvent) => {
      const data = JSON.parse(event.data);
      if (data.error) {
        console.error('WebSocket error:', data.error);
        return;
      }
      
      if (data.type === 'visual') {
        console.log('WebSocket message(visual):', data);
        this.#dispatchEvent('visual', data);
      }
    };
    
    this.#ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.#dispatchEvent('connectionStatus', { type: 'connectionStatus', connected: false });
      this.#checkServerStatus();
    };
    
    this.#ws.onerror = (error: Event) => {
      console.error('WebSocket error:', error);
      this.#dispatchEvent('connectionStatus', { type: 'connectionStatus', connected: false });
      this.#checkServerStatus();
    };
  }

  /**
   * 检查服务器状态并在必要时重新连接
   * @private
   */
  async #checkServerStatus(): Promise<void> {
    try {
      const response = await fetch(`http://${this.host}/api/ping`);
      if (response.ok) {
        this.#connect();
      } else {

        setTimeout(() => this.#checkServerStatus(), 2000);
      }
    } catch {
      setTimeout(() => this.#checkServerStatus(), 2000);
    }
  }

  /**
   * 分发事件到对应的监听器
   * @private
   * @param event - 事件类型
   * @param data - 事件数据
   */
  #dispatchEvent<T extends KotoneDebugEvents>(event: T, data: EventTypeMap<T>): void {
    const listeners = this.#eventListeners[event] as Array<(data: EventTypeMap<T>) => void>;
    listeners.forEach(callback => callback(data));
  }

  async screenshot(): Promise<string> {
    const response = await fetch(`http://${this.host}/api/screenshot`);
    const blob = await response.blob();
    return URL.createObjectURL(blob);
  }

  async runCode(code: string): Promise<RunCodeResultSuccess | RunCodeResultError> {
    const response = await fetch(`http://${this.host}/api/code/run`, {
      method: 'POST',
      body: JSON.stringify({ code }),
      headers: {
        'Content-Type': 'application/json'
      }
    });
    return response.json();


  }


} 