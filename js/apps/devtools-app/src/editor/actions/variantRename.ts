import { messageBox } from "../../ui/messageBox";
import { useAppStore } from "../state";
import { getActiveDocumentId } from "../commands/selectors";
import { useSymbolIndexStore } from "../symbolIndexStore";
import { openImageWithMeta } from "./image";
import i18n from "../../i18n";

interface VariantSymbolRef {
  imagePath: string;
  definitionId: string;
}

async function applyVariantRenames(variantSymbols: VariantSymbolRef[], newName: string): Promise<void> {
  const previousActiveId = getActiveDocumentId();
  const updatesByImagePath = new Map<string, string[]>();
  for (const symbol of variantSymbols) {
    const existing = updatesByImagePath.get(symbol.imagePath);
    if (existing) {
      existing.push(symbol.definitionId);
      continue;
    }
    updatesByImagePath.set(symbol.imagePath, [symbol.definitionId]);
  }

  for (const [imagePath, definitionIds] of updatesByImagePath.entries()) {
    const currentDoc = useAppStore.getState().documents[imagePath];
    if (!currentDoc) {
      await openImageWithMeta(imagePath);
    }
    const targetDoc = useAppStore.getState().documents[imagePath];
    if (!targetDoc || !targetDoc.meta) {
      throw new Error(`Document meta is not loaded: ${imagePath}`);
    }
    useAppStore.getState().setActiveTab(imagePath);
    useAppStore.getState().updateMeta(
      imagePath,
      (draft) => {
        for (const definitionId of definitionIds) {
          const definition = draft.definitions[definitionId];
          if (!definition) {
            throw new Error(`Definition not found: ${definitionId}`);
          }
          if (definition.type !== "prefab" || !definition.variant) {
            throw new Error(`Definition is not a variant prefab: ${definitionId}`);
          }
          definition.name = newName;
        }
      },
      { label: "Rename variant names", mergeKey: "rename:variant-names", forceNewEntry: true }
    );
  }
  if (previousActiveId) {
    useAppStore.getState().setActiveTab(previousActiveId);
  }
}

export async function promptAndRenameVariantsForDefinition(definitionId: string): Promise<void> {
  const activeId = getActiveDocumentId();
  if (!activeId) {
    throw new Error("No active document");
  }
  const { documents } = useAppStore.getState();
  const activeDoc = documents[activeId];
  if (!activeDoc || !activeDoc.meta) {
    throw new Error("Active document has no meta");
  }
  const activeMetaPath = activeDoc.meta.path;

  const definition = activeDoc.meta.data.definitions[definitionId];
  if (!definition) {
    throw new Error(`Definition not found: ${definitionId}`);
  }
  if (definition.type !== "prefab" || !!definition.variant) {
    return;
  }

  const symbols = useSymbolIndexStore.getState().symbols;
  const currentSymbol = symbols.find(
    (symbol) => symbol.type === "prefab" && symbol.metaPath === activeMetaPath && symbol.definitionId === definitionId
  );
  if (!currentSymbol) {
    return;
  }

  const oldName = currentSymbol.name;
  const newName = definition.name ?? "";
  if (oldName === newName) {
    return;
  }

  const variantSymbols = symbols
    .filter((symbol) => symbol.type === "prefab" && !!symbol.variant && symbol.name === oldName)
    .map((symbol) => ({ imagePath: symbol.imagePath, definitionId: symbol.definitionId }));
  if (variantSymbols.length === 0) {
    return;
  }

  const action = await messageBox.show<"auto" | "keep" | "undo">({
    title: i18n.t('variantRename.syncVariantNames'),
    content: i18n.t('variantRename.detectedNameChange', { oldName, newName, count: variantSymbols.length }),
    buttons: [
      { value: "auto", text: i18n.t('variantRename.autoUpdate'), intent: "primary" },
      { value: "keep", text: i18n.t('variantRename.keepAsIs') },
      { value: "undo", text: i18n.t('variantRename.undoChange') },
    ],
    dismissValue: "keep",
    canEscapeKeyClose: true,
    canOutsideClickClose: false,
  });

  if (action === "keep") {
    return;
  }

  if (action === "undo") {
    const current = useAppStore.getState();
    current.updateMeta(
      activeId,
      (draft) => {
        const currentDefinition = draft.definitions[definitionId];
        if (!currentDefinition) {
          throw new Error(`Definition not found: ${definitionId}`);
        }
        currentDefinition.name = oldName;
      },
      { label: "Undo name edit", mergeKey: `prop:${definitionId}:name`, forceNewEntry: true }
    );
    return;
  }

  await applyVariantRenames(variantSymbols, newName);
}
