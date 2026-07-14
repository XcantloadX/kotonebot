import * as vscode from "vscode";
import { LanguageClient } from "vscode-languageclient/node";
import { executeServerCommand } from "../lsp/executeCommand";
import { isMetaDocumentUri } from "../shared/metaPaths";

/** 全量重建 meta 索引命令。 */
const SERVER_COMMAND_META_REFETCH = "server.meta.refetch";
/** 更新单文件 meta 索引命令。 */
const SERVER_COMMAND_META_UPDATE_FILE = "server.meta.updateFile";
/** meta 文件匹配模式。 */
const META_PATTERN = "**/*.png.json";

/** 是否启用保存后自动更新。 */
function shouldAutoRefreshOnSave(): boolean {
  return vscode.workspace.getConfiguration("kotonebot").get<boolean>("autoRefreshOnSave", true);
}

/** 是否启用文件系统变化后自动重建索引。 */
function shouldAutoRefetchOnFsChanges(): boolean {
  return vscode.workspace.getConfiguration("kotonebot").get<boolean>("autoRefetchOnFsChanges", true);
}

/** 读取自动刷新防抖时间。 */
function autoRefreshDebounceMs(): number {
  const value = vscode.workspace.getConfiguration("kotonebot").get<number>("autoRefreshDebounceMs", 300);
  if (value < 50) {
    return 50;
  }
  return value;
}

/** 注册保存与文件变化触发的自动刷新逻辑。 */
export function registerAutoRefresh(context: vscode.ExtensionContext, client: LanguageClient): void {
  let refetchTimer: NodeJS.Timeout | undefined;

  /** 触发防抖后的全量索引刷新。 */
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
