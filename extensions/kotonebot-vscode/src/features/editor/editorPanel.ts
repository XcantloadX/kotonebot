import * as vscode from "vscode";
import { BridgeClient } from "../../bridge/bridgeClient";

/** 打开符号所需的最小定位信息。 */
export interface OpenSymbolPayload {
  /** meta 文件绝对路径。 */
  metaPath: string;
  /** 图片文件绝对路径。 */
  imagePath: string;
  /** definition 唯一标识。 */
  definitionId: string;
}

/** 打开编辑器面板命令 ID。 */
const COMMAND_EDITOR_OPEN = "kotonebot.editor.open";
/** 打开并跳转符号命令 ID。 */
const COMMAND_EDITOR_OPEN_SYMBOL = "kotonebot.editor.openSymbol";
/** 编辑器 Webview 类型标识。 */
const VIEW_TYPE = "kotonebot.editor";

/** 编辑器面板控制器。 */
class EditorPanelController {
  /** 当前编辑器面板实例。 */
  private panel: vscode.WebviewPanel | null = null;
  /** 扩展侧桥接客户端。 */
  private bridge: BridgeClient | null = null;

  /** 创建控制器。 */
  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly getEditorUrl: () => string,
  ) {}

  /** 打开或激活编辑器面板。 */
  openPanel(): void {
    if (this.panel) {
      if (this.panel.visible) {
        return;
      }
      this.panel.reveal(vscode.ViewColumn.Active, false);
      return;
    }
    this.panel = vscode.window.createWebviewPanel(
      VIEW_TYPE,
      "Kotonebot Editor",
      vscode.ViewColumn.Active,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
      },
    );
    this.bridge = new BridgeClient((message) => {
      if (!this.panel) {
        throw new Error("Editor panel is not available");
      }
      this.panel.webview.postMessage(message);
    });
    this.panel.webview.html = this.buildHtml(this.panel.webview, this.getEditorUrl());
    this.panel.onDidDispose(
      () => {
        if (this.bridge) {
          this.bridge.dispose();
        }
        this.bridge = null;
        this.panel = null;
      },
      null,
      this.context.subscriptions,
    );
    this.panel.webview.onDidReceiveMessage(
      (message: unknown) => {
        if (typeof message !== "object" || message === null) {
          return;
        }
        if (!this.bridge) {
          return;
        }
        try {
          this.bridge.handleIncoming(message);
        } catch (err) {
          console.error("[kotonebot.editorPanel] invalid bridge message", err);
        }
      },
      null,
      this.context.subscriptions,
    );
  }

  /** 打开面板并请求内嵌页面跳转到指定符号。 */
  async openSymbol(payload: OpenSymbolPayload): Promise<void> {
    this.openPanel();
    if (!this.bridge) {
      throw new Error("Bridge is not initialized");
    }
    try {
      await this.bridge.request("kotonebot.jumpToSymbol", payload);
    } catch (err) {
      console.error("[kotonebot.editorPanel] jumpToSymbol request failed", err);
      return;
    }
  }

  /** 生成承载 iframe 的 Webview HTML。 */
  private buildHtml(webview: vscode.Webview, editorUrl: string): string {
    const nonce = Math.random().toString(36).slice(2);
    const csp = [
      `default-src 'none'`,
      `img-src ${webview.cspSource} data:`,
      `style-src 'unsafe-inline' ${webview.cspSource}`,
      `script-src 'nonce-${nonce}'`,
      `frame-src http://127.0.0.1:* http://localhost:*`,
      `connect-src http://127.0.0.1:* http://localhost:*`,
    ].join("; ");
    return `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="Content-Security-Policy" content="${csp}" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
      html, body, #editor-frame { margin: 0; padding: 0; width: 100%; height: 100%; border: 0; overflow: hidden; }
      body { background: #f5f8fa; }
    </style>
  </head>
  <body>
    <iframe id="editor-frame" src="${editorUrl}" referrerpolicy="no-referrer"></iframe>
    <script nonce="${nonce}">
      const vscode = acquireVsCodeApi();
      const iframe = document.getElementById("editor-frame");
      iframe.addEventListener("load", () => {
      });
      window.addEventListener("message", (event) => {
        const data = event.data;
        if (!data || typeof data !== "object") {
          return;
        }
        if (event.source === iframe.contentWindow) {
          try {
            vscode.postMessage(data);
          } catch (err) {
            console.error("[kotonebot.editorPanel.webview] failed to forward from iframe", err);
          }
          return;
        }
        try {
          iframe.contentWindow.postMessage(data, "*");
        } catch (err) {
          console.error("[kotonebot.editorPanel.webview] failed to forward to iframe", err);
        }
      });
    </script>
  </body>
</html>`;
  }
}

/** 注册编辑器面板相关命令。 */
export function registerEditorPanel(
  context: vscode.ExtensionContext,
  getEditorUrl: () => string,
): void {
  const controller = new EditorPanelController(context, getEditorUrl);
  context.subscriptions.push(
    vscode.commands.registerCommand(COMMAND_EDITOR_OPEN, () => {
      controller.openPanel();
    }),
  );
  context.subscriptions.push(
    vscode.commands.registerCommand(COMMAND_EDITOR_OPEN_SYMBOL, async (payload: OpenSymbolPayload) => {
      if (typeof payload !== "object" || payload === null) {
        throw new Error("openSymbol payload is required");
      }
      if (typeof payload.metaPath !== "string" || payload.metaPath.trim() === "") {
        throw new Error("openSymbol payload.metaPath is required");
      }
      if (typeof payload.imagePath !== "string" || payload.imagePath.trim() === "") {
        throw new Error("openSymbol payload.imagePath is required");
      }
      if (typeof payload.definitionId !== "string" || payload.definitionId.trim() === "") {
        throw new Error("openSymbol payload.definitionId is required");
      }
      await controller.openSymbol(payload);
    }),
  );
}
