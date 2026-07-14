import * as vscode from "vscode";
import { isMetaDocumentUri, metaToImagePath, imageToMetaPath } from "../../shared/metaPaths";
import { BridgeSessionManager } from "./bridgeSessionManager";
import { defaultMetaContent } from "./documentSyncService";

const VIEW_TYPE = "kotonebot.metaEditor";

export interface OpenSymbolPayload {
  metaPath: string;
  imagePath: string;
  definitionId: string;
}

export class EditorCommandHandler {
  constructor(
    private readonly sessionManager: BridgeSessionManager,
  ) {}

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

  getImageUriFromCommandArg(arg: unknown): vscode.Uri {
    const fromArg = this.tryParseUri(arg);
    if (fromArg && fromArg.scheme === "file" && fromArg.fsPath.toLowerCase().endsWith(".png")) {
      return fromArg;
    }
    const active = this.getActiveResourceUri();
    if (active && active.scheme === "file" && active.fsPath.toLowerCase().endsWith(".png")) {
      return active;
    }
    throw new Error("No active .png document");
  }

  async openMetaInEditor(uri: vscode.Uri): Promise<void> {
    if (!isMetaDocumentUri(uri)) {
      throw new Error(`Unsupported meta document uri: ${uri.toString()}`);
    }
    await this.ensureMetaDocumentExists(uri);
    await vscode.commands.executeCommand("vscode.openWith", uri, VIEW_TYPE);
    if (!this.isMetaTextDocumentDirty(uri)) {
      await this.closeTabsByKind(uri, "text");
    }
  }

  async openMetaInText(uri: vscode.Uri): Promise<void> {
    if (!isMetaDocumentUri(uri)) {
      throw new Error(`Unsupported meta document uri: ${uri.toString()}`);
    }
    await vscode.commands.executeCommand("vscode.openWith", uri, "default");
    await this.closeTabsByKind(uri, "custom");
  }

  async openSymbol(payload: OpenSymbolPayload): Promise<void> {
    const uri = vscode.Uri.file(payload.metaPath);
    await this.openMetaInEditor(uri);
    const session = await this.sessionManager.waitForSession(uri);
    if (!session.panel.visible) {
      session.panel.reveal(vscode.ViewColumn.Active, false);
    }
    try {
      await session.bridge.request("kotonebot.jumpToSymbol", payload);
    } catch (err) {
      console.error("[kotonebot.editorPanel] jumpToSymbol request failed", err);
    }
  }

  async runEditorCommand(uri: vscode.Uri, command: "undo" | "redo" | "save"): Promise<void> {
    await this.openMetaInEditor(uri);
    const session = await this.sessionManager.waitForSession(uri);
    await session.bridge.request("kotonebot.editor.runCommand", { command });
  }

  async ensureMetaDocumentExists(uri: vscode.Uri): Promise<void> {
    try {
      await vscode.workspace.fs.stat(uri);
    } catch {
      await vscode.workspace.fs.writeFile(uri, defaultMetaContent());
    }
  }

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

  private isMetaTextDocumentDirty(uri: vscode.Uri): boolean {
    const hit = vscode.workspace.textDocuments.find((doc) => doc.uri.toString() === uri.toString());
    if (!hit) {
      return false;
    }
    return hit.isDirty;
  }

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
}
