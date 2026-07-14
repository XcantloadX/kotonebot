import type { DiagnosticItem, SymbolLite } from "../../model/symbolIndex";
import { COMMAND_ID } from "./ids";

/** 所有编辑器命令 ID 的联合类型。 */
export type EditorCommandId = typeof COMMAND_ID[keyof typeof COMMAND_ID];

/** 命令参数映射表，键为命令 ID，值为执行该命令所需参数。 */
export interface EditorCommandArgsMap {
  /** 打开命令面板。 */
  [COMMAND_ID.APP_OPEN_COMMAND_PALETTE]: undefined;
  /** 打开设置对话框。 */
  [COMMAND_ID.APP_OPEN_PREFERENCES]: undefined;
  /** 切换问题面板显隐。 */
  [COMMAND_ID.APP_TOGGLE_PROBLEMS_PANEL]: undefined;
  /** 新建文档（打开新建文档对话框）。 */
  [COMMAND_ID.FILE_NEW_DOCUMENT]: undefined;
  /** 打开图片选择对话框。 */
  [COMMAND_ID.FILE_OPEN_IMAGE]: undefined;
  /** 保存当前文档。 */
  [COMMAND_ID.FILE_SAVE]: undefined;
  /** 保存全部脏文档。 */
  [COMMAND_ID.FILE_SAVE_ALL]: undefined;
  /** 重命名当前文档。 */
  [COMMAND_ID.FILE_RENAME]: undefined;
  /** 替换当前文档的图片。 */
  [COMMAND_ID.FILE_REPLACE_IMAGE]: undefined;
  /** 在文件管理器中定位图片。path 为绝对路径；省略时使用当前激活文档。 */
  [COMMAND_ID.FILE_REVEAL_IN_EXPLORER]: { path?: string } | undefined;
  /** 关闭当前激活文档。 */
  [COMMAND_ID.FILE_CLOSE_ACTIVE]: undefined;
  /** 关闭全部文档。 */
  [COMMAND_ID.FILE_CLOSE_ALL]: undefined;
  /** 撤销。 */
  [COMMAND_ID.EDIT_UNDO]: undefined;
  /** 重做。 */
  [COMMAND_ID.EDIT_REDO]: undefined;
  /** 复制当前选中定义并创建副本。 */
  [COMMAND_ID.DEFINITION_DUPLICATE_SELECTED]: undefined;
  /** 复制当前选中定义到内部剪贴板。 */
  [COMMAND_ID.DEFINITION_COPY_SELECTED]: undefined;
  /** 剪切当前选中定义到内部剪贴板。 */
  [COMMAND_ID.DEFINITION_CUT_SELECTED]: undefined;
  /** 删除当前选中定义。 */
  [COMMAND_ID.DEFINITION_DELETE_SELECTED]: undefined;
  /** 从内部剪贴板粘贴定义。 */
  [COMMAND_ID.DEFINITION_PASTE_FROM_CLIPBOARD]: undefined;
  /** 创建新的 variant 图像文档。 */
  [COMMAND_ID.VARIANT_NEW_DOCUMENT]: undefined;
  /** 从剪贴板创建 variant。 */
  [COMMAND_ID.VARIANT_NEW_FROM_CLIPBOARD]: undefined;
  /** 从设备截图创建 variant。 */
  [COMMAND_ID.VARIANT_NEW_FROM_DEVICE]: undefined;
  /** 将当前选中 prefab 复制到 variant。 */
  [COMMAND_ID.VARIANT_COPY_SELECTED_PREFAB]: { variant?: string } | undefined;
  /** 依据定义 ID 重命名关联 variants。 */
  [COMMAND_ID.VARIANT_RENAME_VARIANTS_FOR_DEFINITION]: { definitionId: string };
  /** 按定义 ID 重命名符号名（走服务端 precheck/execute）。 */
  [COMMAND_ID.SYMBOL_RENAME_FOR_DEFINITION]: { definitionId: string; newName: string };
  /** 关闭指定 tab（文档或非文档）。 */
  [COMMAND_ID.TAB_CLOSE]: { id: string };
  /** 关闭除指定 id 外的所有 tab。无参时取 activeTabId。 */
  [COMMAND_ID.TAB_CLOSE_OTHERS]: { id: string } | undefined;
  /** 关闭所有 tab。 */
  [COMMAND_ID.TAB_CLOSE_ALL]: undefined;
  /** 关闭指定文档。 */
  [COMMAND_ID.DOCUMENT_CLOSE]: { id: string };
  /** 批量关闭指定文档。 */
  [COMMAND_ID.DOCUMENT_CLOSE_MANY]: { ids: string[] };
  /** 跳转到目标符号。 */
  [COMMAND_ID.NAVIGATION_JUMP_TO_SYMBOL]: { symbol: SymbolLite };
  /** 跳转到目标诊断项。 */
  [COMMAND_ID.NAVIGATION_JUMP_TO_DIAGNOSTIC]: { diag: DiagnosticItem };
  /** 打开欢迎页。 */
  [COMMAND_ID.APP_OPEN_WELCOME]: undefined;
  /** AI 推断当前选中的 definition。 */
  [COMMAND_ID.AI_INFER_SELECTED]: undefined;
  /** 批量 AI 推断所有 name===null 的 definitions。 */
  [COMMAND_ID.AI_INFER_BATCH]: undefined;
}

/** 无参数命令 ID 集合。 */
export type NoArgCommandId = {
  [K in EditorCommandId]: undefined extends EditorCommandArgsMap[K] ? K : never;
}[EditorCommandId];

/** 由 UI 层提供给命令层的交互入口。 */
export interface EditorCommandUiHandlers {
  /** 打开图片文件对话框。 */
  openImageDialog: () => void;
  /** 打开 variant 目标选择对话框。 */
  openVariantDialog: () => Promise<void>;
  /** 打开设备截图对话框。 */
  openDeviceCaptureDialog: () => Promise<void>;
  /** 打开替换图片对话框。 */
  openReplaceImageDialog: () => void;
  /** 打开偏好设置对话框。 */
  openPreferencesDialog: () => void;
  /** 打开新建文档对话框。 */
  openNewDocumentDialog: () => void;
  /** 打开批量 AI 推断对话框。 */
  openAiBatchDialog: () => Promise<void>;
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
