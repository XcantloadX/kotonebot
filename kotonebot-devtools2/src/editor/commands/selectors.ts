import { useAppStore } from "../state";
import type { DocumentState } from "../state";

/** 读取当前激活文档 ID。 */
export function getActiveDocumentId(): string | null {
  return useAppStore.getState().activeDocumentId;
}

/** 读取当前已打开文档映射。 */
export function getDocuments(): Record<string, DocumentState> {
  return useAppStore.getState().documents;
}

/** 读取当前激活文档。 */
export function getActiveDocument(): DocumentState | null {
  const { activeDocumentId, documents } = useAppStore.getState();
  if (!activeDocumentId) {
    return null;
  }
  return documents[activeDocumentId] ?? null;
}

/** 是否至少存在一个已打开文档。 */
export function hasAnyDocument(): boolean {
  return Object.keys(getDocuments()).length > 0;
}

/** 当前激活文档是否可保存。 */
export function canSaveActiveDocument(): boolean {
  return !!getActiveDocument()?.meta;
}

/** 是否存在可保存的脏文档。 */
export function canSaveAnyDocument(): boolean {
  return Object.values(getDocuments()).some((doc) => doc.dirty);
}

/** 当前激活文档是否可重命名。 */
export function canRenameActiveDocument(): boolean {
  return !!getActiveDocument()?.meta;
}

/** 当前激活文档是否可创建 variant 文档。 */
export function canCreateVariantForActiveDocument(): boolean {
  return !!getActiveDocument()?.meta;
}

/** 当前激活文档是否可执行“复制选中 prefab 到 variant”。 */
export function canCopySelectedPrefabToVariantForActiveDocument(): boolean {
  const activeDoc = getActiveDocument();
  if (!activeDoc?.meta || !activeDoc.selection) {
    return false;
  }
  return activeDoc.meta.data.definitions[activeDoc.selection.definitionId]?.type === "prefab";
}

/** 当前激活文档是否可撤销。 */
export function canUndoInActiveDocument(): boolean {
  const activeDoc = getActiveDocument();
  return !!activeDoc && activeDoc.history.cursor > 0;
}

/** 当前激活文档是否可重做。 */
export function canRedoInActiveDocument(): boolean {
  const activeDoc = getActiveDocument();
  return !!activeDoc && activeDoc.history.cursor < activeDoc.history.entries.length;
}

/** 当前激活文档是否存在可操作的选中 definition。 */
export function canOperateOnSelectedDefinitionInActiveDocument(): boolean {
  const activeDoc = getActiveDocument();
  if (!activeDoc?.meta || !activeDoc.selection) {
    return false;
  }
  return !!activeDoc.meta.data.definitions[activeDoc.selection.definitionId];
}

/** 当前激活文档是否可从内部剪贴板粘贴 definition。 */
export function canPasteDefinitionFromClipboardInActiveDocument(): boolean {
  const state = useAppStore.getState();
  const activeDoc = getActiveDocument();
  if (!activeDoc?.meta) {
    return false;
  }
  return !!state.definitionClipboard;
}
