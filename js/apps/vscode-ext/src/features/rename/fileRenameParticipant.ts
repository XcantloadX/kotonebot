import * as path from "node:path";
import * as vscode from "vscode";
import { LanguageClient } from "vscode-languageclient/node";
import { executeServerCommand } from "../../lsp/executeCommand";
import { imageToMetaPath, isImagePath, isMetaPath, metaToImagePath, normalizePathKey } from "../../shared/metaPaths";

/** 文档重命名预检命令。 */
const SERVER_COMMAND_RENAME_DOCUMENT_PRECHECK = "server.document.rename.precheck";

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
    client: LanguageClient;
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
  });
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

/** 是否在文件重命名时自动补齐 image/meta 成对重命名。 */
function shouldAutoPairRenameOnFileRename(): boolean {
  return vscode.workspace.getConfiguration("kotonebot").get<boolean>("autoPairRenameOnFileRename", true);
}

/** 是否在“改名”场景自动扩展到所有 variant 文档。 */
function shouldAutoVariantRenameOnFileRename(): boolean {
  return vscode.workspace.getConfiguration("kotonebot").get<boolean>("autoVariantRenameOnFileRename", true);
}

/** 注册文件重命名参与者，自动补齐关联文件和 variant 改名。 */
export function registerRenameParticipant(context: vscode.ExtensionContext, client: LanguageClient): void {
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
