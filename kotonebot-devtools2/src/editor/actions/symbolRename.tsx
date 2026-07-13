import React from "react";
import { Intent } from '@blueprintjs/core';
import { executeServerCommand } from "../../api/serverCommands";
import { readText } from "../../api/fs";
import { messageBox } from "../../ui/messageBox";
import { toaster } from "../../ui/toaster";
import { useAppStore } from "../state";
import { useSymbolIndexStore } from "../symbolIndexStore";
import { SERVER_COMMAND_ID } from "../commands/serverIds";
import i18n from "../../i18n";

import { normalizePath } from "../../shared/normalizePath";

/** 单个受影响符号目标。 */
interface RenameSymbolTarget {
  /** 唯一符号键。 */
  symbolKey: string;
  /** 所在 meta 路径。 */
  metaPath: string;
  /** 所在图片路径。 */
  imagePath: string;
  /** definition 标识。 */
  definitionId: string;
  /** 变体名，base 为 null。 */
  variant: string | null;
  /** definition 类型。 */
  type: string;
  /** 原符号名。 */
  oldName: string;
  /** 新符号名。 */
  newName: string;
}

/** 符号重命名预检结果。 */
interface RenameSymbolPrecheckResult {
  /** 触发重命名的源 meta。 */
  sourceMetaPath: string;
  /** 触发重命名的源 definition。 */
  sourceDefinitionId: string;
  /** 原符号名。 */
  oldName: string;
  /** 新符号名。 */
  newName: string;
  /** 受影响目标集合。 */
  targets: RenameSymbolTarget[];
  /** 受影响 meta 文件数。 */
  affectedMetaCount: number;
  /** 受影响 definition 数。 */
  affectedDefinitionCount: number;
}

/** 符号重命名执行结果。 */
interface RenameSymbolExecuteResult extends RenameSymbolPrecheckResult {
  /** 执行后索引版本。 */
  updatedIndexVersion: number;
  /** 执行后索引哈希。 */
  updatedContentHash: string;
}

/** 构建重命名确认弹窗内容（仅展示 meta 文件影响范围）。 */
function buildRenameConfirmContent(precheck: RenameSymbolPrecheckResult): React.ReactNode {
  const affectedMetaPaths = Array.from(new Set(precheck.targets.map((item) => item.metaPath))).sort();
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 900 }}>
      <div style={{ fontWeight: 600 }}>
        {i18n.t('symbolRename.confirmTitle', { oldName: precheck.oldName, newName: precheck.newName })}
      </div>
      <div style={{ fontSize: 12, color: "#5c7080" }}>
        {i18n.t('symbolRename.confirmBody', { defCount: precheck.affectedDefinitionCount, fileCount: precheck.affectedMetaCount })}
      </div>
      <div
        style={{
          maxHeight: 420,
          overflowY: "auto",
          border: "1px solid #d8e1e8",
          borderRadius: 4,
          padding: "10px",
          background: "#f8fbff",
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        {affectedMetaPaths.map((metaPath) => (
          <div
            key={metaPath}
            style={{
              fontFamily: "Consolas, 'Courier New', monospace",
              fontSize: 12,
              color: "#106ba3",
              background: "#ffffff",
              border: "1px solid #d8e1e8",
              borderRadius: 3,
              padding: "6px 8px",
              whiteSpace: "pre-wrap",
              wordBreak: "break-all",
            }}
          >
            {metaPath}
          </div>
        ))}
      </div>
    </div>
  );
}

/** 保存受影响且已打开的脏文档，避免服务端改名覆盖未保存修改。 */
async function saveDirtyAffectedOpenDocuments(affectedMetaPathSet: Set<string>): Promise<void> {
  const current = useAppStore.getState();
  const previousActiveId = current.activeDocumentId;
  const affectedDocIds = Object.values(current.documents)
    .filter((doc) => {
      if (!doc.meta) {
        throw new Error(`Document meta is not loaded: ${doc.id}`);
      }
      return affectedMetaPathSet.has(normalizePath(doc.meta.path));
    })
    .map((doc) => doc.id);

  for (const docId of affectedDocIds) {
    const loopState = useAppStore.getState();
    const doc = loopState.documents[docId];
    if (!doc) {
      throw new Error(`Document not found: ${docId}`);
    }
    if (!doc.meta) {
      throw new Error(`Document meta is not loaded: ${docId}`);
    }
    if (!doc.dirty) {
      continue;
    }
    loopState.setActiveDocument(docId);
    await useAppStore.getState().saveActiveDocument();
  }
  if (previousActiveId) {
    useAppStore.getState().setActiveDocument(previousActiveId);
  }
}

/** 重命名后重新加载受影响且已打开文档的 meta。 */
async function reloadAffectedOpenDocuments(affectedMetaPathSet: Set<string>): Promise<void> {
  const app = useAppStore.getState();
  for (const doc of Object.values(app.documents)) {
    if (!doc.meta) {
      throw new Error(`Document meta is not loaded: ${doc.id}`);
    }
    if (!affectedMetaPathSet.has(normalizePath(doc.meta.path))) {
      continue;
    }
    const content = await readText(doc.meta.path);
    const data = JSON.parse(content);
    if (data.version !== 3) {
      throw new Error(`Unsupported meta version: ${data.version}`);
    }
    useAppStore.getState().setActiveMeta(doc.id, data);
  }
}

/** 对当前激活 definition 执行符号重命名（precheck -> confirm -> execute）。 */
export async function renameSymbolNameForActiveDefinition(definitionId: string, newNameInput: string): Promise<boolean> {
  const state = useAppStore.getState();
  const activeId = state.activeDocumentId;
  if (!activeId) {
    throw new Error("No active document");
  }
  const doc = state.documents[activeId];
  if (!doc || !doc.meta) {
    throw new Error("Active document has no meta");
  }
  const definition = doc.meta.data.definitions[definitionId];
  if (!definition) {
    throw new Error(`Definition not found: ${definitionId}`);
  }
  const oldName = definition.name ?? "";
  const newName = newNameInput.trim();
  if (newName === "") {
    throw new Error("Name cannot be empty");
  }
  if (newName === oldName) {
    return false;
  }

  const precheck = await executeServerCommand<RenameSymbolPrecheckResult>(SERVER_COMMAND_ID.SYMBOL_RENAME_PRECHECK, {
    metaPath: doc.meta.path,
    definitionId,
    newName,
  });
  const confirmed = await messageBox.confirm_cancel({
    title: i18n.t('symbol.confirmRename'),
    content: buildRenameConfirmContent(precheck),
    confirmText: i18n.t('variant.rename'),
    cancelText: i18n.t('dialog.cancel'),
    confirmIntent: "primary",
    cancelIntent: "none",
  });
  if (!confirmed) {
    return false;
  }

  const affectedMetaPathSet = new Set(precheck.targets.map((item) => normalizePath(item.metaPath)));
  await saveDirtyAffectedOpenDocuments(affectedMetaPathSet);
  const result = await executeServerCommand<RenameSymbolExecuteResult>(SERVER_COMMAND_ID.SYMBOL_RENAME_EXECUTE, {
    metaPath: doc.meta.path,
    definitionId,
    newName,
  });
  await reloadAffectedOpenDocuments(affectedMetaPathSet);
  await useSymbolIndexStore.getState().refetch();
  toaster.show({
    message: i18n.t('symbolRename.successToast', { oldName: result.oldName, newName: result.newName, count: result.affectedDefinitionCount }),
    intent: Intent.SUCCESS,
  });
  return true;
}
