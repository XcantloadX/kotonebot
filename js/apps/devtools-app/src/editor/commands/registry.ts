import { editorActions } from "../actions";
import { useAppStore, tabId } from "../state";
import { useSettingsStore } from "../settings";
import { COMMAND_ID } from "./ids";
import {
  canPasteDefinitionFromClipboardInActiveDocument,
  canOperateOnSelectedDefinitionInActiveDocument,
  canCopySelectedPrefabToVariantForActiveDocument,
  canCreateVariantForActiveDocument,
  canRedoInActiveDocument,
  canRenameActiveDocument,
  canReplaceActiveDocumentImage,
  canSaveActiveDocument,
  canSaveAnyDocument,
  canUndoInActiveDocument,
  getActiveDocumentId,
  hasAnyDocument,
  canAiInferSelectedDefinition,
  hasAnyDefinitionWithNullName,
} from "./selectors";
import type { EditorCommandArgsMap, EditorCommandContext, EditorCommandDefinition, EditorCommandId, NoArgCommandId } from "./types";
import i18n from "../../i18n";

const t = (key: string) => i18n.t(key);

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
    title: t('commands.openCommandPalette'),
    keywords: ["command", "palette"],
    showInPalette: false,
    run: async () => {
      const { openCommandPalette } = await import("../actions/app");
      await openCommandPalette();
    },
  },
  [COMMAND_ID.FILE_NEW_DOCUMENT]: {
    id: COMMAND_ID.FILE_NEW_DOCUMENT,
    title: t('menuItem.newDocument'),
    keywords: ["new", "document", "create"],
    showInPalette: true,
    requiredUi: ["openNewDocumentDialog"],
    run: async (ctx) => {
      requireUiHandler(ctx, "openNewDocumentDialog")();
    },
  },
  [COMMAND_ID.APP_OPEN_PREFERENCES]: {
    id: COMMAND_ID.APP_OPEN_PREFERENCES,
    title: t('commands.openPreferences'),
    keywords: ["preferences", "settings", "config"],
    showInPalette: true,
    requiredUi: ["openPreferencesDialog"],
    run: async (ctx) => {
      requireUiHandler(ctx, "openPreferencesDialog")();
    },
  },
  [COMMAND_ID.APP_TOGGLE_PROBLEMS_PANEL]: {
    id: COMMAND_ID.APP_TOGGLE_PROBLEMS_PANEL,
    title: t('commands.toggleProblemsPanel'),
    keywords: ["problems", "diagnostic", "panel"],
    showInPalette: true,
    run: async () => {
      const current = useSettingsStore.getState().problemsVisible;
      useSettingsStore.getState().setProblemsVisible(!current);
    },
  },
  [COMMAND_ID.FILE_OPEN_IMAGE]: {
    id: COMMAND_ID.FILE_OPEN_IMAGE,
    title: t('menuItem.openImage'),
    keywords: ["open", "image", "file"],
    showInPalette: true,
    requiredUi: ["openImageDialog"],
    run: async (ctx) => {
      requireUiHandler(ctx, "openImageDialog")();
    },
  },
  [COMMAND_ID.FILE_SAVE]: {
    id: COMMAND_ID.FILE_SAVE,
    title: t('menuItem.save'),
    keywords: ["save"],
    showInPalette: true,
    when: () => canSaveActiveDocument(),
    run: async () => {
      await editorActions.document.save();
    },
  },
  [COMMAND_ID.FILE_SAVE_ALL]: {
    id: COMMAND_ID.FILE_SAVE_ALL,
    title: t('menuItem.saveAll'),
    keywords: ["save", "all"],
    showInPalette: true,
    when: () => canSaveAnyDocument(),
    run: async () => {
      await editorActions.document.saveAll();
    },
  },
  [COMMAND_ID.FILE_RENAME]: {
    id: COMMAND_ID.FILE_RENAME,
    title: t('commands.renameDocument'),
    keywords: ["rename", "document"],
    showInPalette: true,
    when: () => canRenameActiveDocument(),
    run: async () => {
      await editorActions.document.renameByPrompt();
    },
  },
  [COMMAND_ID.FILE_REPLACE_IMAGE]: {
    id: COMMAND_ID.FILE_REPLACE_IMAGE,
    title: t('commands.replaceImage'),
    keywords: ["replace", "image", "file"],
    showInPalette: true,
    requiredUi: ["openReplaceImageDialog"],
    when: () => canReplaceActiveDocumentImage(),
    run: async (ctx) => {
      requireUiHandler(ctx, "openReplaceImageDialog")();
    },
  },
  [COMMAND_ID.FILE_REVEAL_IN_EXPLORER]: {
    id: COMMAND_ID.FILE_REVEAL_IN_EXPLORER,
    title: t('commands.revealInExplorer'),
    keywords: ["reveal", "explorer", "finder", "locate", "file", "manager"],
    showInPalette: true,
    when: () => !!getActiveDocumentId(),
    run: async (_, args) => {
      const { revealInExplorer } = await import("../../api/fs");
      const path = args?.path ?? useAppStore.getState().documents[getActiveDocumentId()!]?.image.path;
      if (path) await revealInExplorer(path);
    },
  },
  [COMMAND_ID.FILE_CLOSE_ACTIVE]: {
    id: COMMAND_ID.FILE_CLOSE_ACTIVE,
    title: t('menuItem.closeDocument'),
    keywords: ["close", "document"],
    showInPalette: true,
    when: () => !!getActiveDocumentId(),
    run: async () => {
      await editorActions.document.closeActive();
    },
  },
  [COMMAND_ID.FILE_CLOSE_ALL]: {
    id: COMMAND_ID.FILE_CLOSE_ALL,
    title: t('menuItem.closeAllDocuments'),
    keywords: ["close", "all", "document"],
    showInPalette: true,
    when: () => hasAnyDocument(),
    run: async () => {
      await editorActions.document.closeAll();
    },
  },
  [COMMAND_ID.EDIT_UNDO]: {
    id: COMMAND_ID.EDIT_UNDO,
    title: t('menuItem.undo'),
    keywords: ["undo", "history"],
    showInPalette: true,
    when: () => canUndoInActiveDocument(),
    run: async () => {
      const docId = getActiveDocumentId();
      if (docId) useAppStore.getState().undo(docId);
    },
  },
  [COMMAND_ID.EDIT_REDO]: {
    id: COMMAND_ID.EDIT_REDO,
    title: t('menuItem.redo'),
    keywords: ["redo", "history"],
    showInPalette: true,
    when: () => canRedoInActiveDocument(),
    run: async () => {
      const docId = getActiveDocumentId();
      if (docId) useAppStore.getState().redo(docId);
    },
  },
  [COMMAND_ID.DEFINITION_DUPLICATE_SELECTED]: {
    id: COMMAND_ID.DEFINITION_DUPLICATE_SELECTED,
    title: t('commands.duplicateDefinition'),
    keywords: ["definition", "duplicate", "copy"],
    showInPalette: false,
    when: () => canOperateOnSelectedDefinitionInActiveDocument(),
    run: async () => {
      await editorActions.definition.duplicateSelected();
    },
  },
  [COMMAND_ID.DEFINITION_COPY_SELECTED]: {
    id: COMMAND_ID.DEFINITION_COPY_SELECTED,
    title: t('commands.copyDefinition'),
    keywords: ["definition", "copy", "clipboard"],
    showInPalette: false,
    when: () => canOperateOnSelectedDefinitionInActiveDocument(),
    run: async () => {
      await editorActions.definition.copySelected();
    },
  },
  [COMMAND_ID.DEFINITION_CUT_SELECTED]: {
    id: COMMAND_ID.DEFINITION_CUT_SELECTED,
    title: t('commands.cutDefinition'),
    keywords: ["definition", "cut", "clipboard"],
    showInPalette: false,
    when: () => canOperateOnSelectedDefinitionInActiveDocument(),
    run: async () => {
      await editorActions.definition.cutSelected();
    },
  },
  [COMMAND_ID.DEFINITION_DELETE_SELECTED]: {
    id: COMMAND_ID.DEFINITION_DELETE_SELECTED,
    title: t('commands.deleteDefinition'),
    keywords: ["definition", "delete", "remove"],
    showInPalette: false,
    when: () => canOperateOnSelectedDefinitionInActiveDocument(),
    run: async () => {
      await editorActions.definition.deleteSelected();
    },
  },
  [COMMAND_ID.DEFINITION_PASTE_FROM_CLIPBOARD]: {
    id: COMMAND_ID.DEFINITION_PASTE_FROM_CLIPBOARD,
    title: t('commands.pasteDefinition'),
    keywords: ["definition", "paste", "clipboard"],
    showInPalette: false,
    when: () => canPasteDefinitionFromClipboardInActiveDocument(),
    run: async () => {
      await editorActions.definition.pasteFromClipboard();
    },
  },
  [COMMAND_ID.VARIANT_NEW_DOCUMENT]: {
    id: COMMAND_ID.VARIANT_NEW_DOCUMENT,
    title: t('menuItem.newVariantImage'),
    keywords: ["variant", "new", "document"],
    showInPalette: true,
    requiredUi: ["openVariantDialog"],
    when: () => canCreateVariantForActiveDocument(),
    run: async (ctx) => {
      await requireUiHandler(ctx, "openVariantDialog")();
    },
  },
  [COMMAND_ID.VARIANT_NEW_FROM_CLIPBOARD]: {
    id: COMMAND_ID.VARIANT_NEW_FROM_CLIPBOARD,
    title: t('menuItem.newVariantFromClipboard'),
    keywords: ["variant", "clipboard", "new"],
    showInPalette: true,
    when: () => canCreateVariantForActiveDocument(),
    run: async () => {
      await editorActions.variant.importFromClipboardForActive();
    },
  },
  [COMMAND_ID.VARIANT_NEW_FROM_DEVICE]: {
    id: COMMAND_ID.VARIANT_NEW_FROM_DEVICE,
    title: t('menuItem.newVariantFromDevice'),
    keywords: ["variant", "device", "capture", "new"],
    showInPalette: true,
    requiredUi: ["openDeviceCaptureDialog"],
    when: () => canCreateVariantForActiveDocument(),
    run: async (ctx) => {
      await requireUiHandler(ctx, "openDeviceCaptureDialog")();
    },
  },
  [COMMAND_ID.VARIANT_COPY_SELECTED_PREFAB]: {
    id: COMMAND_ID.VARIANT_COPY_SELECTED_PREFAB,
    title: t('menuItem.copyToVariant'),
    keywords: ["variant", "copy", "prefab"],
    showInPalette: true,
    when: () => canCopySelectedPrefabToVariantForActiveDocument(),
    run: async (_, args) => {
      await editorActions.variant.copySelectedPrefabForActive(args?.variant);
    },
  },
  [COMMAND_ID.VARIANT_RENAME_VARIANTS_FOR_DEFINITION]: {
    id: COMMAND_ID.VARIANT_RENAME_VARIANTS_FOR_DEFINITION,
    title: t('commands.renameVariants'),
    keywords: ["variant", "rename", "definition"],
    showInPalette: false,
    run: async (_, args) => {
      await editorActions.variant.renameVariantsForDefinitionByPrompt(args.definitionId);
    },
  },
  [COMMAND_ID.SYMBOL_RENAME_FOR_DEFINITION]: {
    id: COMMAND_ID.SYMBOL_RENAME_FOR_DEFINITION,
    title: t('commands.renameSymbol'),
    keywords: ["symbol", "rename", "definition"],
    showInPalette: false,
    run: async (_, args) => {
      await editorActions.symbol.renameNameForDefinition(args.definitionId, args.newName);
    },
  },
  [COMMAND_ID.TAB_CLOSE]: {
    id: COMMAND_ID.TAB_CLOSE,
    title: t('menuItem.closeDocument'),
    keywords: ["close", "tab"],
    showInPalette: false,
    run: async (_, args) => {
      const state = useAppStore.getState();
      const tab = state.tabs.find(t => tabId(t) === args.id);
      if (!tab) return;
      if (tab.kind === "document") {
        const ok = await editorActions.document.close(tab.docId);
        if (!ok) return;
      } else {
        state.closeTab(args.id);
      }
    },
  },
  [COMMAND_ID.TAB_CLOSE_OTHERS]: {
    id: COMMAND_ID.TAB_CLOSE_OTHERS,
    title: t('tabBar.closeOthers'),
    keywords: ["close", "others", "tab"],
    showInPalette: false,
    run: async (_, args) => {
      const state = useAppStore.getState();
      const keepId = args?.id ?? state.activeTabId ?? "";
      const others = state.tabs.filter(t => tabId(t) !== keepId);
      const docTabs = others.filter(t => t.kind === "document");
      const nonDocIds = others.filter(t => t.kind !== "document").map(tabId);
      if (docTabs.length > 0) {
        const ok = await editorActions.document.closeMany(docTabs.map(t => t.docId));
        if (!ok) return;
      }
      nonDocIds.forEach(id => useAppStore.getState().closeTab(id));
    },
  },
  [COMMAND_ID.TAB_CLOSE_ALL]: {
    id: COMMAND_ID.TAB_CLOSE_ALL,
    title: t('menuItem.closeAllDocuments'),
    keywords: ["close", "all", "tab"],
    showInPalette: false,
    run: async () => {
      const state = useAppStore.getState();
      const docTabs = state.tabs.filter(t => t.kind === "document");
      const nonDocIds = state.tabs.filter(t => t.kind !== "document").map(tabId);
      if (docTabs.length > 0) {
        const ok = await editorActions.document.closeMany(docTabs.map(t => t.docId));
        if (!ok) return;
      }
      nonDocIds.forEach(id => useAppStore.getState().closeTab(id));
    },
  },
  [COMMAND_ID.DOCUMENT_CLOSE]: {
    id: COMMAND_ID.DOCUMENT_CLOSE,
    title: t('menuItem.closeDocument'),
    keywords: ["close", "document"],
    showInPalette: false,
    run: async (_, args) => {
      await editorActions.document.close(args.id);
    },
  },
  [COMMAND_ID.DOCUMENT_CLOSE_MANY]: {
    id: COMMAND_ID.DOCUMENT_CLOSE_MANY,
    title: t('commands.closeDocuments'),
    keywords: ["close", "documents"],
    showInPalette: false,
    run: async (_, args) => {
      await editorActions.document.closeMany(args.ids);
    },
  },
  [COMMAND_ID.NAVIGATION_JUMP_TO_SYMBOL]: {
    id: COMMAND_ID.NAVIGATION_JUMP_TO_SYMBOL,
    title: t('commands.jumpToSymbol'),
    keywords: ["jump", "symbol", "navigate"],
    showInPalette: false,
    run: async (_, args) => {
      await editorActions.navigation.jumpToSymbol(args.symbol);
    },
  },
  [COMMAND_ID.NAVIGATION_JUMP_TO_DIAGNOSTIC]: {
    id: COMMAND_ID.NAVIGATION_JUMP_TO_DIAGNOSTIC,
    title: t('commands.jumpToDiagnostic'),
    keywords: ["jump", "diagnostic", "problem", "navigate"],
    showInPalette: false,
    run: async (_, args) => {
      await editorActions.navigation.jumpToDiagnostic(args.diag);
    },
  },
  [COMMAND_ID.APP_OPEN_WELCOME]: {
    id: COMMAND_ID.APP_OPEN_WELCOME,
    title: t('menuItem.openWelcome'),
    keywords: ["welcome", "start"],
    showInPalette: true,
    run: async () => {
      useAppStore.getState().openTab({ kind: "welcome" });
    },
  },
  [COMMAND_ID.AI_INFER_SELECTED]: {
    id: COMMAND_ID.AI_INFER_SELECTED,
    title: t('menuItem.aiInferSelected'),
    keywords: ["ai", "infer", "fill"],
    showInPalette: true,
    when: () => canAiInferSelectedDefinition(),
    run: async () => {
      await editorActions.ai.inferSingle();
    },
  },
  [COMMAND_ID.AI_INFER_BATCH]: {
    id: COMMAND_ID.AI_INFER_BATCH,
    title: t('menuItem.aiInferBatch'),
    keywords: ["ai", "infer", "batch", "fill"],
    showInPalette: true,
    requiredUi: ["openAiBatchDialog"],
    when: () => hasAnyDefinitionWithNullName(),
    run: async (ctx) => {
      await ctx.ui.openAiBatchDialog!();
    },
  },
  [COMMAND_ID.CONVERSION_SCAN_ALL]: {
    id: COMMAND_ID.CONVERSION_SCAN_ALL,
    title: t('conversion.scanAll'),
    keywords: ["conversion", "scan", "all", "single", "multi"],
    showInPalette: true,
    run: async () => {
      await editorActions.conversion.scanAllDocuments();
    },
  },
  [COMMAND_ID.CONVERSION_SCAN_SPECIFIC]: {
    id: COMMAND_ID.CONVERSION_SCAN_SPECIFIC,
    title: t('conversion.scanSpecific'),
    keywords: ["conversion", "scan", "specific", "single", "multi"],
    showInPalette: true,
    run: async () => {
      await editorActions.conversion.scanWithImages([]);
    },
  },
  [COMMAND_ID.CONVERSION_SCAN_DEVICE]: {
    id: COMMAND_ID.CONVERSION_SCAN_DEVICE,
    title: t('conversion.scanDevice'),
    keywords: ["conversion", "scan", "device", "single", "multi"],
    showInPalette: true,
    run: async () => {
      await editorActions.conversion.scanWithScreenshot("");
    },
  },
  [COMMAND_ID.CONVERSION_EXECUTE]: {
    id: COMMAND_ID.CONVERSION_EXECUTE,
    title: t('conversion.execute'),
    keywords: ["conversion", "execute", "apply"],
    showInPalette: false,
    run: async () => {
      await editorActions.conversion.executeConversion();
    },
  },
};

/** 编辑器命令注册表。 */
export const editorCommandRegistry = commands;

/** 命令面板展示的无参命令 ID 列表。 */
export const paletteCommandIds: NoArgCommandId[] = [
  COMMAND_ID.FILE_NEW_DOCUMENT,
  COMMAND_ID.APP_OPEN_PREFERENCES,
  COMMAND_ID.APP_TOGGLE_PROBLEMS_PANEL,
  COMMAND_ID.FILE_OPEN_IMAGE,
  COMMAND_ID.FILE_SAVE,
  COMMAND_ID.FILE_SAVE_ALL,
  COMMAND_ID.FILE_RENAME,
  COMMAND_ID.FILE_REPLACE_IMAGE,
  COMMAND_ID.FILE_REVEAL_IN_EXPLORER,
  COMMAND_ID.FILE_CLOSE_ACTIVE,
  COMMAND_ID.FILE_CLOSE_ALL,
  COMMAND_ID.EDIT_UNDO,
  COMMAND_ID.EDIT_REDO,
  COMMAND_ID.VARIANT_NEW_DOCUMENT,
  COMMAND_ID.VARIANT_NEW_FROM_CLIPBOARD,
  COMMAND_ID.VARIANT_NEW_FROM_DEVICE,
  COMMAND_ID.VARIANT_COPY_SELECTED_PREFAB,
  COMMAND_ID.APP_OPEN_WELCOME,
  COMMAND_ID.AI_INFER_SELECTED,
  COMMAND_ID.AI_INFER_BATCH,
];

/** 根据命令 ID 推导其参数类型。 */
export type EditorCommandArgs<K extends EditorCommandId> = EditorCommandArgsMap[K];
