import * as vscode from "vscode";
import { LanguageClient } from "vscode-languageclient/node";

const SERVER_COMMAND_META_REFETCH = "server.meta.refetch";
const SERVER_COMMAND_META_UPDATE_FILE = "server.meta.updateFile";
const SERVER_COMMAND_RENAME_DOCUMENT_EXECUTE = "server.document.rename.execute";

export async function executeServerCommand(client: LanguageClient, command: string, args: Record<string, unknown>): Promise<unknown> {
  return client.sendRequest("workspace/executeCommand", { command, arguments: [args] });
}

export function registerCommands(context: vscode.ExtensionContext, client: LanguageClient): void {
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
