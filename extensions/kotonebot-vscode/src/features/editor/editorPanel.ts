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
/** 从文本模式切换到编辑器模式命令 ID。 */
const COMMAND_META_OPEN_EDITOR = "kotonebot.meta.openEditor";
/** 从编辑器模式切换到文本模式命令 ID。 */
const COMMAND_META_OPEN_TEXT = "kotonebot.meta.openText";
/** 编辑器 Custom Editor 类型标识。 */
const VIEW_TYPE = "kotonebot.metaEditor";
/** iframe 请求 host 打开 meta 文档命令 ID。 */
const REQUEST_HOST_OPEN_META_DOCUMENT = "kotonebot.host.openMetaDocument";

function isMetaDocumentUri(uri: vscode.Uri): boolean {
  return uri.scheme === "file" && uri.fsPath.toLowerCase().endsWith(".png.json");
}

function metaToImagePath(metaPath: string): string {
  if (!metaPath.toLowerCase().endsWith(".png.json")) {
    throw new Error(`Meta path must end with .png.json: ${metaPath}`);
  }
  return metaPath.slice(0, -".json".length);
}

interface HostOpenMetaDocumentPayload {
  metaPath: string;
}

/** 编辑器面板控制器。 */
class EditorPanelController implements vscode.CustomTextEditorProvider {
  /** 每个 meta 文档对应的活跃会话。 */
  private readonly sessions = new Map<string, { panel: vscode.WebviewPanel; bridge: BridgeClient }>();

  /** 创建控制器。 */
  constructor(
    private readonly context: vscode.ExtensionContext,
    private readonly getEditorUrl: () => string,
  ) {}

  /** CustomTextEditorProvider 入口。 */
  async resolveCustomTextEditor(
    document: vscode.TextDocument,
    webviewPanel: vscode.WebviewPanel,
    _token: vscode.CancellationToken,
  ): Promise<void> {
    const bridge = new BridgeClient((message) => {
      webviewPanel.webview.postMessage(message);
    });
    const key = document.uri.toString();
    this.sessions.set(key, { panel: webviewPanel, bridge });
    webviewPanel.webview.options = {
      enableScripts: true,
    };
    webviewPanel.webview.html = this.buildHtml(webviewPanel.webview, this.getEditorUrl());
    webviewPanel.onDidDispose(() => {
      bridge.dispose();
      this.sessions.delete(key);
    }, null, this.context.subscriptions);
    webviewPanel.webview.onDidReceiveMessage((message: unknown) => {
      if (typeof message !== "object" || message === null) {
        return;
      }
      try {
        bridge.handleIncoming(message);
      } catch (err) {
        console.error("[kotonebot.metaEditor] invalid bridge message", err);
      }
    }, null, this.context.subscriptions);
    const disposeOpenMetaRequest = bridge.onRequest(REQUEST_HOST_OPEN_META_DOCUMENT, async (payload: unknown) => {
      const parsed = this.parseHostOpenMetaDocumentPayload(payload);
      await this.openMetaInEditor(vscode.Uri.file(parsed.metaPath));
      return { ok: true };
    });
    webviewPanel.onDidDispose(() => {
      disposeOpenMetaRequest();
    }, null, this.context.subscriptions);
    this.openMetaDocument(document.uri, bridge);
  }

  /** 打开面板并请求内嵌页面跳转到指定符号。 */
  async openSymbol(payload: OpenSymbolPayload): Promise<void> {
    const uri = vscode.Uri.file(payload.metaPath);
    await this.openMetaInEditor(uri);
    const session = await this.waitForSession(uri);
    if (!session.panel.visible) {
      session.panel.reveal(vscode.ViewColumn.Active, false);
    }
    try {
      await session.bridge.request("kotonebot.jumpToSymbol", payload);
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
    const iframeUrl = this.withSingleTabMode(editorUrl);
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
    <iframe id="editor-frame" src="${iframeUrl}" referrerpolicy="no-referrer"></iframe>
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

  /** 将 singleTabMode 参数附加到 iframe URL。 */
  private withSingleTabMode(editorUrl: string): string {
    try {
      const url = new URL(editorUrl);
      url.searchParams.set("singleTabMode", "1");
      return url.toString();
    } catch {
      const joiner = editorUrl.includes("?") ? "&" : "?";
      return `${editorUrl}${joiner}singleTabMode=1`;
    }
  }

  /** 在编辑器模式中打开指定 meta 文档。 */
  async openMetaInEditor(uri: vscode.Uri): Promise<void> {
    if (!isMetaDocumentUri(uri)) {
      throw new Error(`Unsupported meta document uri: ${uri.toString()}`);
    }
    await vscode.commands.executeCommand("vscode.openWith", uri, VIEW_TYPE);
    if (!this.isMetaTextDocumentDirty(uri)) {
      await this.closeTabsByKind(uri, "text");
    }
  }

  /** 在文本模式中打开指定 meta 文档。 */
  async openMetaInText(uri: vscode.Uri): Promise<void> {
    if (!isMetaDocumentUri(uri)) {
      throw new Error(`Unsupported meta document uri: ${uri.toString()}`);
    }
    await vscode.commands.executeCommand("vscode.openWith", uri, "default");
    await this.closeTabsByKind(uri, "custom");
  }

  /** 获取命令上下文中的 meta 文档 URI。 */
  getMetaUriFromCommandArg(arg: unknown): vscode.Uri {
    const fromArg = this.tryParseUri(arg);
    if (fromArg && isMetaDocumentUri(fromArg)) {
      return fromArg;
    }
    const active = this.getActiveResourceUri();
    if (active && isMetaDocumentUri(active)) {
      return active;
    }
    throw new Error("No active .png.json document");
  }

  /** 解析当前激活 Tab 对应的资源 URI。 */
  private getActiveResourceUri(): vscode.Uri | null {
    const textEditor = vscode.window.activeTextEditor;
    if (textEditor) {
      return textEditor.document.uri;
    }
    const tab = vscode.window.tabGroups.activeTabGroup.activeTab;
    if (!tab) {
      return null;
    }
    if (tab.input instanceof vscode.TabInputText) {
      return tab.input.uri;
    }
    if (tab.input instanceof vscode.TabInputCustom) {
      return tab.input.uri;
    }
    return null;
  }

  /** 从命令参数中提取 URI。 */
  private tryParseUri(arg: unknown): vscode.Uri | null {
    if (arg instanceof vscode.Uri) {
      return arg;
    }
    if (typeof arg !== "object" || arg === null) {
      return null;
    }
    const value = arg as { fsPath?: unknown };
    if (typeof value.fsPath === "string" && value.fsPath.trim() !== "") {
      return vscode.Uri.file(value.fsPath);
    }
    return null;
  }

  /** 收集某个 URI 对应且匹配输入类型的所有 tab。 */
  private collectTabsByKind(uri: vscode.Uri, kind: "text" | "custom"): vscode.Tab[] {
    const uriKey = uri.toString();
    const result: vscode.Tab[] = [];
    for (const group of vscode.window.tabGroups.all) {
      for (const tab of group.tabs) {
        if (kind === "text") {
          if (!(tab.input instanceof vscode.TabInputText)) {
            continue;
          }
          if (tab.input.uri.toString() === uriKey) {
            result.push(tab);
          }
          continue;
        }
        if (!(tab.input instanceof vscode.TabInputCustom)) {
          continue;
        }
        if (tab.input.uri.toString() === uriKey) {
          result.push(tab);
        }
      }
    }
    return result;
  }

  /** 关闭指定 URI 的某一类 tab。 */
  private async closeTabsByKind(uri: vscode.Uri, kind: "text" | "custom"): Promise<void> {
    const tabs = this.collectTabsByKind(uri, kind);
    if (tabs.length === 0) {
      return;
    }
    try {
      await vscode.window.tabGroups.close(tabs);
    } catch (err) {
      console.warn(`[kotonebot.metaEditor] close ${kind} tabs failed`, err);
    }
  }

  /** 判断 meta 文本文档是否存在未保存改动。 */
  private isMetaTextDocumentDirty(uri: vscode.Uri): boolean {
    const hit = vscode.workspace.textDocuments.find((doc) => doc.uri.toString() === uri.toString());
    if (!hit) {
      return false;
    }
    return hit.isDirty;
  }

  /** 等待目标文档对应的 editor 会话就绪。 */
  private async waitForSession(uri: vscode.Uri, timeoutMs = 6000): Promise<{ panel: vscode.WebviewPanel; bridge: BridgeClient }> {
    const key = uri.toString();
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const session = this.sessions.get(key);
      if (session) {
        return session;
      }
      await new Promise<void>((resolve) => {
        setTimeout(() => resolve(), 40);
      });
    }
    throw new Error(`Meta editor session not ready: ${uri.fsPath}`);
  }

  /** 请求 iframe 打开指定 meta 文档。 */
  private openMetaDocument(uri: vscode.Uri, bridge: BridgeClient): void {
    const metaPath = uri.fsPath;
    const imagePath = metaToImagePath(metaPath);
    bridge.send("kotonebot.openMetaDocument", { metaPath, imagePath });
  }

  /** 解析 iframe 发来的 host 打开文档请求。 */
  private parseHostOpenMetaDocumentPayload(value: unknown): HostOpenMetaDocumentPayload {
    if (typeof value !== "object" || value === null) {
      throw new Error(`${REQUEST_HOST_OPEN_META_DOCUMENT} payload is required`);
    }
    const payload = value as Partial<HostOpenMetaDocumentPayload>;
    if (typeof payload.metaPath !== "string" || payload.metaPath.trim() === "") {
      throw new Error(`${REQUEST_HOST_OPEN_META_DOCUMENT} payload.metaPath is required`);
    }
    if (!payload.metaPath.toLowerCase().endsWith(".png.json")) {
      throw new Error(`${REQUEST_HOST_OPEN_META_DOCUMENT} payload.metaPath must end with .png.json: ${payload.metaPath}`);
    }
    return payload as HostOpenMetaDocumentPayload;
  }
}

/** 注册编辑器面板相关命令。 */
export function registerEditorPanel(
  context: vscode.ExtensionContext,
  getEditorUrl: () => string,
): void {
  const controller = new EditorPanelController(context, getEditorUrl);
  context.subscriptions.push(
    vscode.window.registerCustomEditorProvider(VIEW_TYPE, controller, {
      webviewOptions: {
        retainContextWhenHidden: true,
      },
      supportsMultipleEditorsPerDocument: false,
    }),
  );
  context.subscriptions.push(
    vscode.commands.registerCommand(COMMAND_EDITOR_OPEN, async (arg: unknown) => {
      const uri = controller.getMetaUriFromCommandArg(arg);
      await controller.openMetaInEditor(uri);
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
  context.subscriptions.push(
    vscode.commands.registerCommand(COMMAND_META_OPEN_EDITOR, async (arg: unknown) => {
      const uri = controller.getMetaUriFromCommandArg(arg);
      await controller.openMetaInEditor(uri);
    }),
  );
  context.subscriptions.push(
    vscode.commands.registerCommand(COMMAND_META_OPEN_TEXT, async (arg: unknown) => {
      const uri = controller.getMetaUriFromCommandArg(arg);
      await controller.openMetaInText(uri);
    }),
  );
}
