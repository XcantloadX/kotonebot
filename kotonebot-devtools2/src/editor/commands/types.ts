import type { DiagnosticItem, SymbolLite } from "../../model/symbolIndex";
import { COMMAND_ID } from "./ids";

/** 所有编辑器命令 ID 的联合类型。 */
export type EditorCommandId = typeof COMMAND_ID[keyof typeof COMMAND_ID];

/** 命令参数映射表，键为命令 ID，值为执行该命令所需参数。 */
export interface EditorCommandArgsMap {
  /** 打开命令面板。 */
  [COMMAND_ID.APP_OPEN_COMMAND_PALETTE]: undefined;
  /** 切换问题面板显隐。 */
  [COMMAND_ID.APP_TOGGLE_PROBLEMS_PANEL]: undefined;
  /** 打开图片选择对话框。 */
  [COMMAND_ID.FILE_OPEN_IMAGE]: undefined;
  /** 保存当前文档。 */
  [COMMAND_ID.FILE_SAVE]: undefined;
  /** 保存全部脏文档。 */
  [COMMAND_ID.FILE_SAVE_ALL]: undefined;
  /** 重命名当前文档。 */
  [COMMAND_ID.FILE_RENAME]: undefined;
  /** 关闭当前激活文档。 */
  [COMMAND_ID.FILE_CLOSE_ACTIVE]: undefined;
  /** 关闭全部文档。 */
  [COMMAND_ID.FILE_CLOSE_ALL]: undefined;
  /** 撤销。 */
  [COMMAND_ID.EDIT_UNDO]: undefined;
  /** 重做。 */
  [COMMAND_ID.EDIT_REDO]: undefined;
  /** 创建新的 variant 图像文档。 */
  [COMMAND_ID.VARIANT_NEW_DOCUMENT]: undefined;
  /** 将当前选中 prefab 复制到 variant。 */
  [COMMAND_ID.VARIANT_COPY_SELECTED_PREFAB]: undefined;
  /** 依据定义 ID 重命名关联 variants。 */
  [COMMAND_ID.VARIANT_RENAME_VARIANTS_FOR_DEFINITION]: { definitionId: string };
  /** 关闭指定文档。 */
  [COMMAND_ID.DOCUMENT_CLOSE]: { id: string };
  /** 批量关闭指定文档。 */
  [COMMAND_ID.DOCUMENT_CLOSE_MANY]: { ids: string[] };
  /** 跳转到目标符号。 */
  [COMMAND_ID.NAVIGATION_JUMP_TO_SYMBOL]: { symbol: SymbolLite };
  /** 跳转到目标诊断项。 */
  [COMMAND_ID.NAVIGATION_JUMP_TO_DIAGNOSTIC]: { diag: DiagnosticItem };
}

/** 无参数命令 ID 集合。 */
export type NoArgCommandId = {
  [K in EditorCommandId]: EditorCommandArgsMap[K] extends undefined ? K : never;
}[EditorCommandId];

/** 由 UI 层提供给命令层的交互入口。 */
export interface EditorCommandUiHandlers {
  /** 打开命令面板。 */
  openCommandPalette: () => void;
  /** 打开图片文件对话框。 */
  openImageDialog: () => void;
  /** 打开 variant 目标选择对话框。 */
  openVariantDialog: () => Promise<void>;
  /** 执行“复制选中 prefab 到 variant”流程。 */
  copySelectedPrefabToVariant: () => Promise<void>;
}

/** 命令执行上下文。 */
export interface EditorCommandContext {
  /** 当前可用的 UI 回调集合。 */
  ui: Partial<EditorCommandUiHandlers>;
}

/** 单条命令定义。 */
export interface EditorCommandDefinition<K extends EditorCommandId> {
  /** 命令唯一 ID。 */
  id: K;
  /** 展示名称。 */
  title: string;
  /** 搜索关键词。 */
  keywords?: readonly string[];
  /** 是否在命令面板展示。 */
  showInPalette: boolean;
  /** 执行该命令所需的 UI 回调。 */
  requiredUi?: readonly (keyof EditorCommandUiHandlers)[];
  /** 启用态判定。 */
  when?: (args: EditorCommandArgsMap[K]) => boolean;
  /** 执行函数。 */
  run: (ctx: EditorCommandContext, args: EditorCommandArgsMap[K]) => Promise<void>;
}
