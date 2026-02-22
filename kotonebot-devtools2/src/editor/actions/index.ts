import {
  closeActiveDocumentWithChecks,
  closeAllDocumentsWithChecks,
  closeDocumentWithChecks,
  closeDocumentsWithChecks,
} from "./close";
import {
  copySelectedDefinition,
  cutSelectedDefinition,
  deleteSelectedDefinition,
  duplicateSelectedDefinition,
  pasteDefinitionFromClipboard,
} from "./definition";
import { openImageWithMeta, openImagesWithChecks } from "./image";
import { jumpToDiagnostic, jumpToSymbol } from "./navigation";
import { promptAndRenameActiveDocument } from "./rename";
import { saveActiveDocumentWithToast, saveAllDocumentsWithToast } from "./save";
import {
  copySelectedPrefabToVariantForActiveDocument,
  importVariantImageForActiveDocument,
  loadProjectVariants,
  pickVariantForActiveDocument,
  selectVariantImageForActiveDocument,
} from "./variant";
import { promptAndRenameVariantsForDefinition } from "./variantRename";

const imageActions = {
  /** 打开单个图片并加载其元数据。 */
  openWithMeta: openImageWithMeta,
  /** 批量打开图片并执行必要检查。 */
  openWithChecks: openImagesWithChecks,
};

const documentActions = {
  /** 保存当前文档并显示结果提示。 */
  save: saveActiveDocumentWithToast,
  /** 保存全部脏文档并显示结果提示。 */
  saveAll: saveAllDocumentsWithToast,
  /** 通过输入框重命名当前文档。 */
  renameByPrompt: promptAndRenameActiveDocument,
  /** 尝试关闭指定文档，必要时提示保存。 */
  close: closeDocumentWithChecks,
  /** 依次尝试关闭多个文档，遇到取消即中断。 */
  closeMany: closeDocumentsWithChecks,
  /** 尝试关闭当前激活文档。 */
  closeActive: closeActiveDocumentWithChecks,
  /** 尝试关闭所有打开文档。 */
  closeAll: closeAllDocumentsWithChecks,
};

const variantActions = {
  /** 读取项目可选 Variant 列表。 */
  loadOptions: loadProjectVariants,
  /** 为当前文档弹窗选择目标 Variant。 */
  pickForActive: pickVariantForActiveDocument,
  /** 基于当前文档将指定图片设为目标 Variant。 */
  selectImageForActive: selectVariantImageForActiveDocument,
  /** 为当前文档导入一个 Variant 图片。 */
  importImageForActive: importVariantImageForActiveDocument,
  /** 将当前选中 prefab 复制到指定 Variant。 */
  copySelectedPrefabForActive: copySelectedPrefabToVariantForActiveDocument,
  /** 基于当前定义批量重命名相关 Variant。 */
  renameVariantsForDefinitionByPrompt: promptAndRenameVariantsForDefinition,
};

const navigationActions = {
  /** 跳转到指定符号。 */
  jumpToSymbol,
  /** 跳转到指定诊断项。 */
  jumpToDiagnostic,
};

const definitionActions = {
  copySelected: copySelectedDefinition,
  cutSelected: cutSelectedDefinition,
  deleteSelected: deleteSelectedDefinition,
  duplicateSelected: duplicateSelectedDefinition,
  pasteFromClipboard: pasteDefinitionFromClipboard,
};

export const editorActions = {
  image: imageActions,
  document: documentActions,
  variant: variantActions,
  navigation: navigationActions,
  definition: definitionActions,
};
