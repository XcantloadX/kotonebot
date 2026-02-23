import * as vscode from "vscode";
import { createLanguageClient } from "./client";
import { executeServerCommand, registerCommands } from "./commands";
import { registerSymbolTree } from "./symbolTree";

let clientStopped: Promise<void> | undefined;
const SERVER_COMMAND_META_REFETCH = "server.meta.refetch";
const SERVER_COMMAND_META_UPDATE_FILE = "server.meta.updateFile";
const META_PATTERN = "**/*.png.json";

function isMetaDocumentUri(uri: vscode.Uri): boolean {
  return uri.scheme === "file" && uri.fsPath.toLowerCase().endsWith(".png.json");
}

function shouldAutoRefreshOnSave(): boolean {
  return vscode.workspace.getConfiguration("kotonebot").get<boolean>("autoRefreshOnSave", true);
}

function shouldAutoRefetchOnFsChanges(): boolean {
  return vscode.workspace.getConfiguration("kotonebot").get<boolean>("autoRefetchOnFsChanges", true);
}

function autoRefreshDebounceMs(): number {
  const value = vscode.workspace.getConfiguration("kotonebot").get<number>("autoRefreshDebounceMs", 300);
  if (value < 50) {
    return 50;
  }
  return value;
}

function registerAutoRefresh(context: vscode.ExtensionContext, client: ReturnType<typeof createLanguageClient>): void {
  let refetchTimer: NodeJS.Timeout | undefined;

  const triggerRefetch = (): void => {
    if (!shouldAutoRefetchOnFsChanges()) {
      return;
    }
    if (refetchTimer) {
      clearTimeout(refetchTimer);
    }
    refetchTimer = setTimeout(() => {
      executeServerCommand(client, SERVER_COMMAND_META_REFETCH, {}).catch((err: unknown) => {
        console.warn("Kotonebot auto refetch failed", err);
      });
    }, autoRefreshDebounceMs());
  };

  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument((document) => {
      if (!shouldAutoRefreshOnSave()) {
        return;
      }
      if (!isMetaDocumentUri(document.uri)) {
        return;
      }
      executeServerCommand(client, SERVER_COMMAND_META_UPDATE_FILE, { metaPath: document.uri.fsPath }).catch((err: unknown) => {
        console.warn("Kotonebot auto update meta index failed", err);
      });
    }),
  );

  const watcher = vscode.workspace.createFileSystemWatcher(META_PATTERN);
  context.subscriptions.push(watcher);
  context.subscriptions.push(
    watcher.onDidCreate((uri) => {
      if (isMetaDocumentUri(uri)) {
        triggerRefetch();
      }
    }),
  );
  context.subscriptions.push(
    watcher.onDidDelete((uri) => {
      if (isMetaDocumentUri(uri)) {
        triggerRefetch();
      }
    }),
  );
  context.subscriptions.push(
    watcher.onDidChange((uri) => {
      if (isMetaDocumentUri(uri)) {
        triggerRefetch();
      }
    }),
  );

  context.subscriptions.push({
    dispose: () => {
      if (refetchTimer) {
        clearTimeout(refetchTimer);
        refetchTimer = undefined;
      }
    },
  });
}

export async function activate(context: vscode.ExtensionContext): Promise<void> {
  const client = createLanguageClient(context);
  context.subscriptions.push({
    dispose: () => {
      clientStopped = client.stop();
    },
  });
  await client.start();
  registerCommands(context, client);
  registerSymbolTree(context, client);
  registerAutoRefresh(context, client);
}

export async function deactivate(): Promise<void> {
  if (clientStopped) {
    await clientStopped;
  }
}
