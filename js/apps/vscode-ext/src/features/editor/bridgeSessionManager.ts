import * as vscode from "vscode";
import { BridgeClient } from "../../bridge/bridgeClient";

interface EditorSession {
  panel: vscode.WebviewPanel;
  bridge: BridgeClient;
}

export class BridgeSessionManager implements vscode.Disposable {
  private readonly sessions = new Map<string, EditorSession>();

  createSession(key: string, panel: vscode.WebviewPanel, bridge: BridgeClient): void {
    this.sessions.set(key, { panel, bridge });
  }

  getSession(uri: vscode.Uri): EditorSession | undefined {
    return this.sessions.get(uri.toString());
  }

  removeSession(key: string): void {
    this.sessions.delete(key);
  }

  async waitForSession(uri: vscode.Uri, timeoutMs = 6000): Promise<EditorSession> {
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

  dispose(): void {
    for (const [key, session] of this.sessions) {
      session.bridge.dispose();
    }
    this.sessions.clear();
  }
}
