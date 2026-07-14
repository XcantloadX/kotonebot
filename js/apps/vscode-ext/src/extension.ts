import * as vscode from "vscode";
import { LanguageClient } from "vscode-languageclient/node";
import { createLanguageClient, getDevtoolsServerConfig, getEditorBaseUrl } from "./lsp/client";
import { registerCommands } from "./features/commands";
import { registerAutoRefresh } from "./features/autoRefresh";
import { registerEditorPanel } from "./features/editor/editorPanel";
import { registerRSymbolHover } from "./features/hover/rSymbolHover";
import { registerRenameParticipant } from "./features/rename/fileRenameParticipant";
import { registerSymbolTree } from "./features/symbols/symbolTree";

/** 扩展激活入口。 */
export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const server = getDevtoolsServerConfig();
  const editorUrl = getEditorBaseUrl(server);
  registerEditorPanel(context, () => editorUrl);

  // LSP 启动——独立 try/catch，失败不影响其他功能
  let client: LanguageClient | null = null;
  try {
    client = createLanguageClient(context);
    context.subscriptions.push({
      dispose: () => {
        client?.stop().catch((e: unknown) => console.error("[kotonebot] LSP stop error:", e));
      },
    });
    await client.start();
  } catch (e) {
    vscode.window.showErrorMessage(
      `KotoneBot LSP 启动失败: ${e instanceof Error ? e.message : String(e)}。请检查 "kotonebot.lspCommand" 配置。`
    );
  }

  registerCommands(context, client);
  registerSymbolTree(context, client);
  registerRSymbolHover(context, server);
  registerRenameParticipant(context, client);
  registerAutoRefresh(context, client);
}

/** 扩展停用入口。生命周期由 context.subscriptions 管理。 */
export async function deactivate(): Promise<void> {
}
