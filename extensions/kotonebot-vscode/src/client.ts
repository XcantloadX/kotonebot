import * as vscode from "vscode";
import { LanguageClient, LanguageClientOptions, ServerOptions, TransportKind } from "vscode-languageclient/node";

export function createLanguageClient(context: vscode.ExtensionContext): LanguageClient {
  const lspCommand = vscode.workspace.getConfiguration("kotonebot").get<string>("lspCommand") || "kbot";
  const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  const args = ["devtools-lsp"];
  if (workspaceFolder) {
    args.push("--workspace", workspaceFolder);
  }
  const serverOptions: ServerOptions = {
    command: lspCommand,
    args,
    transport: TransportKind.stdio,
  };
  const clientOptions: LanguageClientOptions = {
    documentSelector: [{ scheme: "file", pattern: "**/*.png.json" }],
  };
  return new LanguageClient("kotonebot-devtools", "Kotonebot Devtools", serverOptions, clientOptions);
}
