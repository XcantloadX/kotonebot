import { editorActions } from "../actions";
import { useAppStore } from "../state";
import { useSettingsStore } from "../settings";
import { COMMAND_ID } from "./ids";
import {
  canPasteDefinitionFromClipboardInActiveDocument,
  canOperateOnSelectedDefinitionInActiveDocument,
  canCopySelectedPrefabToVariantForActiveDocument,
  canCreateVariantForActiveDocument,
  canRedoInActiveDocument,
  canRenameActiveDocument,
  canSaveActiveDocument,
  canSaveAnyDocument,
  canUndoInActiveDocument,
  getActiveDocumentId,
  hasAnyDocument,
} from "./selectors";
import type { EditorCommandArgsMap, EditorCommandContext, EditorCommandDefinition, EditorCommandId, NoArgCommandId } from "./types";

/** 读取命令依赖的 UI 回调；缺失时直接抛错。 */
function requireUiHandler<K extends keyof EditorCommandContext["ui"]>(
  ctx: EditorCommandContext,
  key: K,
): NonNullable<EditorCommandContext["ui"][K]> {
  const handler = ctx.ui[key];
  if (!handler) {
    throw new Error(`UI handler '${key}' is required for this command`);
  }
  return handler;
}

/** 命令注册表定义。 */
const commands: { [K in EditorCommandId]: EditorCommandDefinition<K> } = {
  [COMMAND_ID.APP_OPEN_COMMAND_PALETTE]: {
    id: COMMAND_ID.APP_OPEN_COMMAND_PALETTE,
    title: "Open Command Palette",
    keywords: ["command", "palette"],
    showInPalette: false,
    requiredUi: ["openCommandPalette"],
    run: async (ctx) => {
      requireUiHandler(ctx, "openCommandPalette")();
    },
  },
  [COMMAND_ID.APP_TOGGLE_PROBLEMS_PANEL]: {
    id: COMMAND_ID.APP_TOGGLE_PROBLEMS_PANEL,
    title: "Toggle Problems Panel",
    keywords: ["problems", "diagnostic", "panel"],
    showInPalette: true,
    run: async () => {
      const current = useSettingsStore.getState().problemsVisible;
      useSettingsStore.getState().setProblemsVisible(!current);
    },
  },
  [COMMAND_ID.FILE_OPEN_IMAGE]: {
    id: COMMAND_ID.FILE_OPEN_IMAGE,
    title: "Open Image...",
    keywords: ["open", "image", "file"],
    showInPalette: true,
    requiredUi: ["openImageDialog"],
    run: async (ctx) => {
      requireUiHandler(ctx, "openImageDialog")();
    },
  },
  [COMMAND_ID.FILE_SAVE]: {
    id: COMMAND_ID.FILE_SAVE,
    title: "Save",
    keywords: ["save"],
    showInPalette: true,
    when: () => canSaveActiveDocument(),
    run: async () => {
      await editorActions.document.save();
    },
  },
  [COMMAND_ID.FILE_SAVE_ALL]: {
    id: COMMAND_ID.FILE_SAVE_ALL,
    title: "Save All",
    keywords: ["save", "all"],
    showInPalette: true,
    when: () => canSaveAnyDocument(),
    run: async () => {
      await editorActions.document.saveAll();
    },
  },
  [COMMAND_ID.FILE_RENAME]: {
    id: COMMAND_ID.FILE_RENAME,
    title: "Rename Document...",
    keywords: ["rename", "document"],
    showInPalette: true,
    when: () => canRenameActiveDocument(),
    run: async () => {
      await editorActions.document.renameByPrompt();
    },
  },
  [COMMAND_ID.FILE_CLOSE_ACTIVE]: {
    id: COMMAND_ID.FILE_CLOSE_ACTIVE,
    title: "Close Document",
    keywords: ["close", "document"],
    showInPalette: true,
    when: () => !!getActiveDocumentId(),
    run: async () => {
      await editorActions.document.closeActive();
    },
  },
  [COMMAND_ID.FILE_CLOSE_ALL]: {
    id: COMMAND_ID.FILE_CLOSE_ALL,
    title: "Close All Documents",
    keywords: ["close", "all", "document"],
    showInPalette: true,
    when: () => hasAnyDocument(),
    run: async () => {
      await editorActions.document.closeAll();
    },
  },
  [COMMAND_ID.EDIT_UNDO]: {
    id: COMMAND_ID.EDIT_UNDO,
    title: "Undo",
    keywords: ["undo", "history"],
    showInPalette: true,
    when: () => canUndoInActiveDocument(),
    run: async () => {
      useAppStore.getState().undo();
    },
  },
  [COMMAND_ID.EDIT_REDO]: {
    id: COMMAND_ID.EDIT_REDO,
    title: "Redo",
    keywords: ["redo", "history"],
    showInPalette: true,
    when: () => canRedoInActiveDocument(),
    run: async () => {
      useAppStore.getState().redo();
    },
  },
  [COMMAND_ID.DEFINITION_DUPLICATE_SELECTED]: {
    id: COMMAND_ID.DEFINITION_DUPLICATE_SELECTED,
    title: "Duplicate Selected Definition",
    keywords: ["definition", "duplicate", "copy"],
    showInPalette: false,
    when: () => canOperateOnSelectedDefinitionInActiveDocument(),
    run: async () => {
      await editorActions.definition.duplicateSelected();
    },
  },
  [COMMAND_ID.DEFINITION_COPY_SELECTED]: {
    id: COMMAND_ID.DEFINITION_COPY_SELECTED,
    title: "Copy Selected Definition",
    keywords: ["definition", "copy", "clipboard"],
    showInPalette: false,
    when: () => canOperateOnSelectedDefinitionInActiveDocument(),
    run: async () => {
      await editorActions.definition.copySelected();
    },
  },
  [COMMAND_ID.DEFINITION_CUT_SELECTED]: {
    id: COMMAND_ID.DEFINITION_CUT_SELECTED,
    title: "Cut Selected Definition",
    keywords: ["definition", "cut", "clipboard"],
    showInPalette: false,
    when: () => canOperateOnSelectedDefinitionInActiveDocument(),
    run: async () => {
      await editorActions.definition.cutSelected();
    },
  },
  [COMMAND_ID.DEFINITION_DELETE_SELECTED]: {
    id: COMMAND_ID.DEFINITION_DELETE_SELECTED,
    title: "Delete Selected Definition",
    keywords: ["definition", "delete", "remove"],
    showInPalette: false,
    when: () => canOperateOnSelectedDefinitionInActiveDocument(),
    run: async () => {
      await editorActions.definition.deleteSelected();
    },
  },
  [COMMAND_ID.DEFINITION_PASTE_FROM_CLIPBOARD]: {
    id: COMMAND_ID.DEFINITION_PASTE_FROM_CLIPBOARD,
    title: "Paste Definition From Clipboard",
    keywords: ["definition", "paste", "clipboard"],
    showInPalette: false,
    when: () => canPasteDefinitionFromClipboardInActiveDocument(),
    run: async () => {
      await editorActions.definition.pasteFromClipboard();
    },
  },
  [COMMAND_ID.VARIANT_NEW_DOCUMENT]: {
    id: COMMAND_ID.VARIANT_NEW_DOCUMENT,
    title: "New Variant Image Document...",
    keywords: ["variant", "new", "document"],
    showInPalette: true,
    requiredUi: ["openVariantDialog"],
    when: () => canCreateVariantForActiveDocument(),
    run: async (ctx) => {
      await requireUiHandler(ctx, "openVariantDialog")();
    },
  },
  [COMMAND_ID.VARIANT_COPY_SELECTED_PREFAB]: {
    id: COMMAND_ID.VARIANT_COPY_SELECTED_PREFAB,
    title: "Copy Selected Prefab to Variant",
    keywords: ["variant", "copy", "prefab"],
    showInPalette: true,
    when: () => canCopySelectedPrefabToVariantForActiveDocument(),
    run: async (_, args) => {
      await editorActions.variant.copySelectedPrefabForActive(args?.variant);
    },
  },
  [COMMAND_ID.VARIANT_RENAME_VARIANTS_FOR_DEFINITION]: {
    id: COMMAND_ID.VARIANT_RENAME_VARIANTS_FOR_DEFINITION,
    title: "Rename Variants for Definition",
    keywords: ["variant", "rename", "definition"],
    showInPalette: false,
    run: async (_, args) => {
      await editorActions.variant.renameVariantsForDefinitionByPrompt(args.definitionId);
    },
  },
  [COMMAND_ID.DOCUMENT_CLOSE]: {
    id: COMMAND_ID.DOCUMENT_CLOSE,
    title: "Close Document",
    keywords: ["close", "document"],
    showInPalette: false,
    run: async (_, args) => {
      await editorActions.document.close(args.id);
    },
  },
  [COMMAND_ID.DOCUMENT_CLOSE_MANY]: {
    id: COMMAND_ID.DOCUMENT_CLOSE_MANY,
    title: "Close Documents",
    keywords: ["close", "documents"],
    showInPalette: false,
    run: async (_, args) => {
      await editorActions.document.closeMany(args.ids);
    },
  },
  [COMMAND_ID.NAVIGATION_JUMP_TO_SYMBOL]: {
    id: COMMAND_ID.NAVIGATION_JUMP_TO_SYMBOL,
    title: "Jump To Symbol",
    keywords: ["jump", "symbol", "navigate"],
    showInPalette: false,
    run: async (_, args) => {
      await editorActions.navigation.jumpToSymbol(args.symbol);
    },
  },
  [COMMAND_ID.NAVIGATION_JUMP_TO_DIAGNOSTIC]: {
    id: COMMAND_ID.NAVIGATION_JUMP_TO_DIAGNOSTIC,
    title: "Jump To Diagnostic",
    keywords: ["jump", "diagnostic", "problem", "navigate"],
    showInPalette: false,
    run: async (_, args) => {
      await editorActions.navigation.jumpToDiagnostic(args.diag);
    },
  },
};

/** 编辑器命令注册表。 */
export const editorCommandRegistry = commands;

/** 命令面板展示的无参命令 ID 列表。 */
export const paletteCommandIds: NoArgCommandId[] = [
  COMMAND_ID.APP_TOGGLE_PROBLEMS_PANEL,
  COMMAND_ID.FILE_OPEN_IMAGE,
  COMMAND_ID.FILE_SAVE,
  COMMAND_ID.FILE_SAVE_ALL,
  COMMAND_ID.FILE_RENAME,
  COMMAND_ID.FILE_CLOSE_ACTIVE,
  COMMAND_ID.FILE_CLOSE_ALL,
  COMMAND_ID.EDIT_UNDO,
  COMMAND_ID.EDIT_REDO,
  COMMAND_ID.VARIANT_NEW_DOCUMENT,
  COMMAND_ID.VARIANT_COPY_SELECTED_PREFAB,
];

/** 根据命令 ID 推导其参数类型。 */
export type EditorCommandArgs<K extends EditorCommandId> = EditorCommandArgsMap[K];
