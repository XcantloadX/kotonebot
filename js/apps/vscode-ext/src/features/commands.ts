import * as vscode from "vscode";
import type { LanguageClient } from "vscode-languageclient/node";
import { executeServerCommand } from "../lsp/executeCommand";

/** 刷新 meta 索引命令。 */
const SERVER_COMMAND_META_REFETCH = "server.meta.refetch";
/** 更新单文件 meta 索引命令。 */
const SERVER_COMMAND_META_UPDATE_FILE = "server.meta.updateFile";
/** 执行文档重命名命令。 */
const SERVER_COMMAND_RENAME_DOCUMENT_EXECUTE = "server.document.rename.execute";

/** 注册扩展命令入口。 */
export function registerCommands(context: vscode.ExtensionContext, client: LanguageClient | null): void {
  if (!client) return;
  context.subscriptions.push(
    vscode.commands.registerCommand("kotonebot.refreshDiagnostics", async () => {
      await executeServerCommand(client, SERVER_COMMAND_META_REFETCH, {});
      vscode.window.showInformationMessage("Kotonebot diagnostics refreshed.");
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("kotonebot.updateMetaIndex", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        throw new Error("No active editor");
      }
      await executeServerCommand(client, SERVER_COMMAND_META_UPDATE_FILE, { metaPath: editor.document.uri.fsPath });
      vscode.window.showInformationMessage("Kotonebot meta index updated.");
    }),
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("kotonebot.renameDocumentPair", async () => {
      const sourceImagePath = await vscode.window.showInputBox({ prompt: "Source image path" });
      if (!sourceImagePath) {
        throw new Error("sourceImagePath is required");
      }
      const targetImagePath = await vscode.window.showInputBox({ prompt: "Target image path" });
      if (!targetImagePath) {
        throw new Error("targetImagePath is required");
      }
      await executeServerCommand(client, SERVER_COMMAND_RENAME_DOCUMENT_EXECUTE, { sourceImagePath, targetImagePath });
      vscode.window.showInformationMessage("Kotonebot document rename executed.");
    }),
  );
}
