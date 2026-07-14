import * as vscode from "vscode";
import type { LanguageClient } from "vscode-languageclient/node";
import {
  META_PATTERN,
  SYMBOL_TREE_REFRESH_COMMAND,
  SYMBOL_TREE_RENAME_COMMAND,
  SYMBOL_TREE_VIEW_ID,
} from "./constants";
import { SymbolTreeProvider } from "./provider";
import { isSymbolNode, renameSymbolByNode } from "./renameFlow";
import { SymbolTreeNode } from "./types";

/** 注册符号树视图、命令与自动刷新监听。 */
export function registerSymbolTree(context: vscode.ExtensionContext, client: LanguageClient | null): void {
  if (!client) return;
  const provider = new SymbolTreeProvider(client);
  context.subscriptions.push(vscode.window.createTreeView(SYMBOL_TREE_VIEW_ID, { treeDataProvider: provider }));

  context.subscriptions.push(
    vscode.commands.registerCommand(SYMBOL_TREE_REFRESH_COMMAND, async () => {
      await provider.refresh();
    }),
  );
  context.subscriptions.push(
    vscode.commands.registerCommand(SYMBOL_TREE_RENAME_COMMAND, async (node: SymbolTreeNode | undefined) => {
      if (node === undefined || !isSymbolNode(node)) {
        throw new Error("kotonebot.symbolTree.rename requires a symbol tree node");
      }
      await renameSymbolByNode(client, provider, node);
    }),
  );

  const watcher = vscode.workspace.createFileSystemWatcher(META_PATTERN);
  context.subscriptions.push(watcher);
  context.subscriptions.push(watcher.onDidCreate(async () => provider.refresh()));
  context.subscriptions.push(watcher.onDidDelete(async () => provider.refresh()));
  context.subscriptions.push(watcher.onDidChange(async () => provider.refresh()));
  context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(async () => provider.refresh()));

  provider.refresh().catch((err: unknown) => {
    void vscode.window.showErrorMessage(`Kotonebot symbol tree refresh failed: ${String(err)}`);
  });
}
