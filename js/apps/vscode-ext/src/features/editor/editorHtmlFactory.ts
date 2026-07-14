import * as vscode from "vscode";

function withSingleTabMode(editorUrl: string): string {
  try {
    const url = new URL(editorUrl);
    url.searchParams.set("singleTabMode", "1");
    return url.toString();
  } catch {
    const joiner = editorUrl.includes("?") ? "&" : "?";
    return `${editorUrl}${joiner}singleTabMode=1`;
  }
}

export function createEditorHtml(webview: vscode.Webview, editorUrl: string): string {
  const nonce = Math.random().toString(36).slice(2);
  const csp = [
    `default-src 'none'`,
    `img-src ${webview.cspSource} data:`,
    `style-src 'unsafe-inline' ${webview.cspSource}`,
    `script-src 'nonce-${nonce}'`,
    `frame-src http://127.0.0.1:* http://localhost:*`,
    `connect-src http://127.0.0.1:* http://localhost:*`,
  ].join("; ");
  const iframeUrl = withSingleTabMode(editorUrl);
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
