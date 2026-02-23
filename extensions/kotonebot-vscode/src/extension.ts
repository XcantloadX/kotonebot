import * as vscode from "vscode";
import * as path from "node:path";
import { createLanguageClient, getDevtoolsServerConfig, getEditorBaseUrl } from "./lsp/client";
import { executeServerCommand, registerCommands } from "./features/commands";
import { registerEditorPanel } from "./features/editor/editorPanel";
import { registerRSymbolHover } from "./features/hover/rSymbolHover";
import { registerSymbolTree } from "./features/symbols/symbolTree";

/** 客户端停止 Promise 缓存。 */
let clientStopped: Promise<void> | undefined;
/** 全量重建 meta 索引命令。 */
const SERVER_COMMAND_META_REFETCH = "server.meta.refetch";
/** 更新单文件 meta 索引命令。 */
const SERVER_COMMAND_META_UPDATE_FILE = "server.meta.updateFile";
/** 文档重命名预检命令。 */
const SERVER_COMMAND_RENAME_DOCUMENT_PRECHECK = "server.document.rename.precheck";
/** meta 文件匹配模式。 */
const META_PATTERN = "**/*.png.json";

/** 判断 URI 是否为 meta 文档。 */
function isMetaDocumentUri(uri: vscode.Uri): boolean {
  return uri.scheme === "file" && uri.fsPath.toLowerCase().endsWith(".png.json");
}

/** 判断路径是否为 meta 文件（*.png.json）。 */
function isMetaPath(fsPath: string): boolean {
  return fsPath.toLowerCase().endsWith(".png.json");
}

/** 判断路径是否为图片文件（*.png）。 */
function isImagePath(fsPath: string): boolean {
  return fsPath.toLowerCase().endsWith(".png");
}

/** 将 meta 文件路径映射为对应图片路径。 */
function metaToImagePath(metaPath: string): string {
  if (!isMetaPath(metaPath)) {
    throw new Error(`Meta path must end with .png.json: ${metaPath}`);
  }
  return metaPath.slice(0, -".json".length);
}

/** 将图片路径映射为对应 meta 路径。 */
function imageToMetaPath(imagePath: string): string {
  if (!isImagePath(imagePath)) {
    throw new Error(`Image path must end with .png: ${imagePath}`);
  }
  return `${imagePath}.json`;
}

/** 统一路径格式用于比较和去重。 */
function normalizePathKey(fsPath: string): string {
  return fsPath.split("\\").join("/").toLowerCase();
}

/** 单次文件重命名解析出的业务意图。 */
interface RenameIntent {
  /** 源图片绝对路径。 */
  sourceImagePath: string;
  /** 目标图片绝对路径。 */
  targetImagePath: string;
  /** 用户本次直接操作的是 meta 还是图片。 */
  sourceKind: "meta" | "image";
  /** 业务模式：改名或仅移动。 */
  mode: "rename" | "move";
}

/** 预检返回的单条文件重命名计划。 */
interface RenameFileItem {
  /** 文件类型。 */
  kind: "image" | "meta";
  /** 所属变体（base/en/...）。 */
  variant: string;
  /** 源文件绝对路径。 */
  sourcePath: string;
  /** 目标文件绝对路径。 */
  targetPath: string;
}

/** 文档重命名预检返回结构。 */
interface RenameDocumentPrecheckResult {
  /** 是否存在冲突。 */
  hasConflicts: boolean;
  /** 冲突详情列表。 */
  conflicts: string[];
  /** 计划执行的文件重命名列表。 */
  fileRenames: RenameFileItem[];
}

/** 将 VS Code 的文件重命名项解析为扩展内部意图。 */
function parseRenameIntent(item: { oldUri: vscode.Uri; newUri: vscode.Uri }): RenameIntent | null {
  if (item.oldUri.scheme !== "file" || item.newUri.scheme !== "file") {
    return null;
  }
  const oldPath = item.oldUri.fsPath;
  const newPath = item.newUri.fsPath;
  const oldIsMeta = isMetaPath(oldPath);
  const oldIsImage = isImagePath(oldPath);
  if (!oldIsMeta && !oldIsImage) {
    return null;
  }
  const newIsMeta = isMetaPath(newPath);
  const newIsImage = isImagePath(newPath);
  if (!newIsMeta && !newIsImage) {
    throw new Error(`Kotonebot only supports renaming *.png or *.png.json files: ${newPath}`);
  }
  if (oldIsMeta !== newIsMeta || oldIsImage !== newIsImage) {
    throw new Error(`Rename target must keep file type (${oldPath} -> ${newPath})`);
  }
  const sourceImagePath = oldIsMeta ? metaToImagePath(oldPath) : oldPath;
  const targetImagePath = newIsMeta ? metaToImagePath(newPath) : newPath;
  const sourceName = path.basename(sourceImagePath);
  const targetName = path.basename(targetImagePath);
  return {
    sourceImagePath,
    targetImagePath,
    sourceKind: oldIsMeta ? "meta" : "image",
    mode: sourceName === targetName ? "move" : "rename",
  };
}

/** 检查文件是否存在。 */
async function fileExists(uri: vscode.Uri): Promise<boolean> {
  try {
    await vscode.workspace.fs.stat(uri);
    return true;
  } catch {
    return false;
  }
}

/** 判断一条补充重命名是否与用户原始重命名一致。 */
function ensureUserRenameCompatible(userRenameMap: Map<string, string>, sourcePath: string, targetPath: string): "skip" | "apply" {
  const sourceKey = normalizePathKey(sourcePath);
  const targetKey = normalizePathKey(targetPath);
  const userTarget = userRenameMap.get(sourceKey);
  if (userTarget !== undefined) {
    if (userTarget !== targetKey) {
      throw new Error(`Rename conflict with user operation: ${sourcePath} -> ${targetPath}`);
    }
    return "skip";
  }
  return "apply";
}

/** 向 WorkspaceEdit 追加重命名，并在 plannedMap 中去重。 */
function appendRenameEdit(
  edit: vscode.WorkspaceEdit,
  plannedMap: Map<string, string>,
  sourcePath: string,
  targetPath: string,
): boolean {
  const sourceKey = normalizePathKey(sourcePath);
  const targetKey = normalizePathKey(targetPath);
  const existing = plannedMap.get(sourceKey);
  if (existing !== undefined) {
    if (existing !== targetKey) {
      throw new Error(`Duplicate planned rename with different target: ${sourcePath}`);
    }
    return false;
  }
  plannedMap.set(sourceKey, targetKey);
  edit.renameFile(vscode.Uri.file(sourcePath), vscode.Uri.file(targetPath), {
    overwrite: false,
    ignoreIfExists: false,
  });
  return true;
}

/** 处理“仅移动”场景：只补齐图片和 meta 成对移动，不动 variant。 */
async function applyMovePairRename(
  {
    intent,
    userRenameMap,
    edit,
    plannedMap,
  }: {
    intent: RenameIntent;
    userRenameMap: Map<string, string>;
    edit: vscode.WorkspaceEdit;
    plannedMap: Map<string, string>;
  },
): Promise<void> {
  const sourceCounterpartPath = intent.sourceKind === "image"
    ? imageToMetaPath(intent.sourceImagePath)
    : intent.sourceImagePath;
  const targetCounterpartPath = intent.sourceKind === "image"
    ? imageToMetaPath(intent.targetImagePath)
    : intent.targetImagePath;
  if (intent.sourceKind === "meta") {
    const sourceImagePath = intent.sourceImagePath;
    const targetImagePath = intent.targetImagePath;
    if (!(await fileExists(vscode.Uri.file(sourceImagePath)))) {
      throw new Error(`Source image does not exist for meta move: ${sourceImagePath}`);
    }
    if (ensureUserRenameCompatible(userRenameMap, sourceImagePath, targetImagePath) === "apply") {
      appendRenameEdit(edit, plannedMap, sourceImagePath, targetImagePath);
    }
    return;
  }
  if (!(await fileExists(vscode.Uri.file(sourceCounterpartPath)))) {
    throw new Error(`Source meta does not exist for image move: ${sourceCounterpartPath}`);
  }
  if (ensureUserRenameCompatible(userRenameMap, sourceCounterpartPath, targetCounterpartPath) === "apply") {
    appendRenameEdit(edit, plannedMap, sourceCounterpartPath, targetCounterpartPath);
  }
}

/** 处理“改名”场景：通过服务端预检拿到完整计划，包含 variant。 */
async function applyRenameWithVariants(
  {
    client,
    intent,
    includeVariants,
    userRenameMap,
    edit,
    plannedMap,
  }: {
    client: ReturnType<typeof createLanguageClient>;
    intent: RenameIntent;
    includeVariants: boolean;
    userRenameMap: Map<string, string>;
    edit: vscode.WorkspaceEdit;
    plannedMap: Map<string, string>;
  },
): Promise<void> {
  const precheck = await executeServerCommand(client, SERVER_COMMAND_RENAME_DOCUMENT_PRECHECK, {
    sourceImagePath: intent.sourceImagePath,
    targetImagePath: intent.targetImagePath,
  }) as RenameDocumentPrecheckResult;
  if (precheck.hasConflicts) {
    throw new Error(`Cannot rename document:\n${precheck.conflicts.join("\n")}`);
  }
  const sourceImageKey = normalizePathKey(intent.sourceImagePath);
  const sourceImageRename = precheck.fileRenames.find(
    (item) => item.kind === "image" && normalizePathKey(item.sourcePath) === sourceImageKey,
  );
  if (!sourceImageRename) {
    throw new Error(`Rename precheck missing source image plan: ${intent.sourceImagePath}`);
  }
  const sourceVariant = sourceImageRename.variant;
  const selectedRenames = includeVariants
    ? precheck.fileRenames
    : precheck.fileRenames.filter((item) => item.variant === sourceVariant);
  for (const item of selectedRenames) {
    const sourcePath = item.sourcePath;
    const targetPath = item.targetPath;
    const decision = ensureUserRenameCompatible(userRenameMap, sourcePath, targetPath);
    if (decision === "skip") {
      continue;
    }
    appendRenameEdit(edit, plannedMap, sourcePath, targetPath);
  }
}

/** 注册文件重命名参与者，自动补齐关联文件和 variant 改名。 */
function registerRenameParticipant(context: vscode.ExtensionContext, client: ReturnType<typeof createLanguageClient>): void {
  const syntheticRenamePairs = new Set<string>();
  const renamePairKey = (oldPath: string, newPath: string): string =>
    `${normalizePathKey(oldPath)}=>${normalizePathKey(newPath)}`;

  context.subscriptions.push(
    vscode.workspace.onWillRenameFiles((event) => {
      event.waitUntil((async () => {
        try {
          const effectiveFiles: Array<{ oldUri: vscode.Uri; newUri: vscode.Uri }> = [];
          for (const item of event.files) {
            const key = renamePairKey(item.oldUri.fsPath, item.newUri.fsPath);
            if (syntheticRenamePairs.has(key)) {
              syntheticRenamePairs.delete(key);
              continue;
            }
            effectiveFiles.push(item);
          }
          if (effectiveFiles.length === 0) {
            return undefined;
          }
          const pairRenameEnabled = shouldAutoPairRenameOnFileRename();
          const variantRenameEnabled = shouldAutoVariantRenameOnFileRename();
          if (!pairRenameEnabled && !variantRenameEnabled) {
            return undefined;
          }

          const userRenameMap = new Map<string, string>();
          for (const item of effectiveFiles) {
            if (item.oldUri.scheme !== "file" || item.newUri.scheme !== "file") {
              continue;
            }
            userRenameMap.set(normalizePathKey(item.oldUri.fsPath), normalizePathKey(item.newUri.fsPath));
          }

          const intentsByKey = new Map<string, RenameIntent>();
          for (const item of effectiveFiles) {
            const intent = parseRenameIntent(item);
            if (!intent) {
              continue;
            }
            const key = `${normalizePathKey(intent.sourceImagePath)}=>${normalizePathKey(intent.targetImagePath)}`;
            const existing = intentsByKey.get(key);
            if (!existing) {
              intentsByKey.set(key, intent);
              continue;
            }
            if (existing.mode !== intent.mode) {
              throw new Error(`Inconsistent rename mode for same document: ${intent.sourceImagePath}`);
            }
          }

          const edit = new vscode.WorkspaceEdit();
          const plannedMap = new Map<string, string>();
          for (const intent of intentsByKey.values()) {
            if (intent.mode === "move") {
              if (!pairRenameEnabled) {
                continue;
              }
              await applyMovePairRename({ intent, userRenameMap, edit, plannedMap });
              continue;
            }
            if (!pairRenameEnabled) {
              continue;
            }
            await applyRenameWithVariants({
              client,
              intent,
              includeVariants: variantRenameEnabled,
              userRenameMap,
              edit,
              plannedMap,
            });
          }
          if (plannedMap.size === 0) {
            return undefined;
          }
          for (const [sourceKey, targetKey] of plannedMap.entries()) {
            syntheticRenamePairs.add(`${sourceKey}=>${targetKey}`);
          }
          return edit;
        } catch (err: unknown) {
          void vscode.window.showErrorMessage(`Kotonebot rename handling failed: ${String(err)}`);
          throw err;
        }
      })());
    }),
  );
}

/** 是否启用保存后自动更新。 */
function shouldAutoRefreshOnSave(): boolean {
  return vscode.workspace.getConfiguration("kotonebot").get<boolean>("autoRefreshOnSave", true);
}

/** 是否在文件重命名时自动补齐 image/meta 成对重命名。 */
function shouldAutoPairRenameOnFileRename(): boolean {
  return vscode.workspace.getConfiguration("kotonebot").get<boolean>("autoPairRenameOnFileRename", true);
}

/** 是否在“改名”场景自动扩展到所有 variant 文档。 */
function shouldAutoVariantRenameOnFileRename(): boolean {
  return vscode.workspace.getConfiguration("kotonebot").get<boolean>("autoVariantRenameOnFileRename", true);
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
function registerAutoRefresh(context: vscode.ExtensionContext, client: ReturnType<typeof createLanguageClient>): void {
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
