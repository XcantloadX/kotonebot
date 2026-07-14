export const SERVER_COMMAND_ID = {
  META_REFETCH: "server.meta.refetch",
  META_UPDATE_FILE: "server.meta.updateFile",
  DOCUMENT_RENAME_EXECUTE: "server.document.rename.execute",
  DOCUMENT_RENAME_PRECHECK: "server.document.rename.precheck",
  SYMBOL_RENAME_PRECHECK: "server.symbol.rename.precheck",
  SYMBOL_RENAME_EXECUTE: "server.symbol.rename.execute",
  VARIANT_CLONE_TO_IMAGE: "server.variant.cloneToImage",
  VARIANT_IMPORT_IMAGE: "server.variant.importImage",
  VARIANT_COPY_SELECTED_PREFAB_PRECHECK: "server.variant.copySelectedPrefab.precheck",
} as const;
