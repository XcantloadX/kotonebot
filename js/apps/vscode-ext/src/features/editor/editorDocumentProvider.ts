import * as vscode from "vscode";
import { BridgeClient } from "../../bridge/bridgeClient";
import { metaToImagePath } from "../../shared/metaPaths";
import { BridgeSessionManager } from "./bridgeSessionManager";
import { createEditorHtml } from "./editorHtmlFactory";
import { parseEditorDocumentStatePayload, syncMetaTextDocument } from "./documentSyncService";
import { EditorCommandHandler } from "./editorCommandHandler";

const REQUEST_HOST_OPEN_META_DOCUMENT = "kotonebot.host.openMetaDocument";

export class EditorDocumentProvider implements vscode.CustomTextEditorProvider {
  constructor(
    private readonly getEditorUrl: () => string,
    private readonly sessionManager: BridgeSessionManager,
    private readonly commandHandler: EditorCommandHandler,
  ) {}

  async resolveCustomTextEditor(
    document: vscode.TextDocument,
    webviewPanel: vscode.WebviewPanel,
    _token: vscode.CancellationToken,
  ): Promise<void> {
    const panelDisposables: vscode.Disposable[] = [];
    const disposeOnPanelClose = (): void => {
      for (const d of panelDisposables) {
        d.dispose();
      }
    };

    const bridge = new BridgeClient((message) => {
      webviewPanel.webview.postMessage(message);
    });
    const key = document.uri.toString();
    this.sessionManager.createSession(key, webviewPanel, bridge);

    webviewPanel.webview.options = {
      enableScripts: true,
    };
    webviewPanel.webview.html = createEditorHtml(webviewPanel.webview, this.getEditorUrl());

    webviewPanel.onDidDispose(() => {
      bridge.dispose();
      this.sessionManager.removeSession(key);
      disposeOnPanelClose();
    });

    webviewPanel.webview.onDidReceiveMessage((message: unknown) => {
      if (typeof message !== "object" || message === null) {
        return;
      }
      try {
        bridge.handleIncoming(message);
      } catch (err) {
        console.error("[kotonebot.metaEditor] invalid bridge message", err);
      }
    });

    const disposeOpenMetaRequest = bridge.onRequest(REQUEST_HOST_OPEN_META_DOCUMENT, async (payload: unknown) => {
      const parsed = parseHostOpenMetaDocumentPayload(payload);
      await this.commandHandler.openMetaInEditor(vscode.Uri.file(parsed.metaPath));
      return { ok: true };
    });

    const disposeDocumentState = bridge.on("kotonebot.editor.documentState", (message) => {
      const parsed = parseEditorDocumentStatePayload(message.payload);
      void syncMetaTextDocument(parsed).catch((err: unknown) => {
        console.warn("[kotonebot.metaEditor] sync document state failed", err);
      });
    });

    panelDisposables.push(
      { dispose: disposeOpenMetaRequest },
      { dispose: disposeDocumentState },
    );

    this.openMetaDocument(document.uri, bridge);
  }

  private openMetaDocument(uri: vscode.Uri, bridge: BridgeClient): void {
    const metaPath = uri.fsPath;
    const imagePath = metaToImagePath(metaPath);
    bridge.send("kotonebot.openMetaDocument", { metaPath, imagePath });
  }
}

interface HostOpenMetaDocumentPayload {
  metaPath: string;
}

function parseHostOpenMetaDocumentPayload(value: unknown): HostOpenMetaDocumentPayload {
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
