import * as vscode from "vscode";
import { createLanguageClient, getDevtoolsServerConfig, getEditorBaseUrl } from "./lsp/client";
import { registerCommands } from "./features/commands";
import { registerAutoRefresh } from "./features/autoRefresh";
import { registerEditorPanel } from "./features/editor/editorPanel";
import { registerRSymbolHover } from "./features/hover/rSymbolHover";
import { registerRenameParticipant } from "./features/rename/fileRenameParticipant";
import { registerSymbolTree } from "./features/symbols/symbolTree";

/** 客户端停止 Promise 缓存。 */
let clientStopped: Promise<void> | undefined;
/** 扩展激活入口。 */
export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const server = getDevtoolsServerConfig();
  const editorUrl = getEditorBaseUrl(server);
  registerEditorPanel(context, () => editorUrl);
  const client = createLanguageClient(context);
  context.subscriptions.push({
    dispose: () => {
      clientStopped = client.stop();
    },
  });
  await client.start();
  registerCommands(context, client);
  registerSymbolTree(context, client);
  registerRSymbolHover(context, server);
  registerRenameParticipant(context, client);
  registerAutoRefresh(context, client);
}

/** 扩展停用入口。 */
export async function deactivate(): Promise<void> {
  if (clientStopped) {
    await clientStopped;
  }
}
