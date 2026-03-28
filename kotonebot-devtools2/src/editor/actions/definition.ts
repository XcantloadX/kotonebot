import { v4 as uuidv4 } from "uuid";
import type { DefinitionV2 } from "../../model/metaV2";
import { useAppStore } from "../state";

function deepCloneDefinition(definition: DefinitionV2): DefinitionV2 {
  return JSON.parse(JSON.stringify(definition)) as DefinitionV2;
}

function getActiveDefinitionOrThrow(): { definitionId: string; definition: DefinitionV2 } {
  const { activeDocumentId, documents } = useAppStore.getState();
  if (!activeDocumentId) {
    throw new Error("No active document");
  }
  const activeDoc = documents[activeDocumentId];
  if (!activeDoc) {
    throw new Error(`Active document not found: ${activeDocumentId}`);
  }
  if (!activeDoc.meta) {
    throw new Error(`Active document has no meta: ${activeDocumentId}`);
  }
  if (!activeDoc.selection) {
    throw new Error("No selected definition");
  }
  const definitionId = activeDoc.selection.definitionId;
  const definition = activeDoc.meta.data.definitions[definitionId];
  if (!definition) {
    throw new Error(`Definition not found: ${definitionId}`);
  }
  return { definitionId, definition };
}

export async function copySelectedDefinition(): Promise<void> {
  const { setDefinitionClipboard } = useAppStore.getState();
  const { definitionId, definition } = getActiveDefinitionOrThrow();
  setDefinitionClipboard({
    sourceDefinitionId: definitionId,
    definition: deepCloneDefinition(definition),
  });
}

export async function duplicateSelectedDefinition(): Promise<void> {
  const { updateMeta, setSelection } = useAppStore.getState();
  const { definition } = getActiveDefinitionOrThrow();
  const duplicatedId = uuidv4();
  const duplicatedDefinition = deepCloneDefinition(definition);
  updateMeta((draft) => {
    draft.definitions[duplicatedId] = duplicatedDefinition;
  }, {
    label: "Duplicate definition",
    forceNewEntry: true,
  });
  setSelection(duplicatedId);
}

export async function deleteSelectedDefinition(): Promise<void> {
  const { updateMeta, setSelection, setMode } = useAppStore.getState();
  const { definitionId } = getActiveDefinitionOrThrow();
  updateMeta((draft) => {
    delete draft.definitions[definitionId];
  }, {
    label: "Delete definition",
    mergeKey: `delete:${definitionId}`,
    forceNewEntry: true,
  });
  setSelection(null);
  setMode({ kind: "idle" });
}

export async function cutSelectedDefinition(): Promise<void> {
  const { setDefinitionClipboard, updateMeta, setSelection, setMode } = useAppStore.getState();
  const { definitionId, definition } = getActiveDefinitionOrThrow();
  setDefinitionClipboard({
    sourceDefinitionId: definitionId,
    definition: deepCloneDefinition(definition),
  });
  updateMeta((draft) => {
    delete draft.definitions[definitionId];
  }, {
    label: "Cut definition",
    mergeKey: `cut:${definitionId}`,
    forceNewEntry: true,
  });
  setSelection(null);
  setMode({ kind: "idle" });
}

export async function selectDefinition(definitionId: string | null): Promise<void> {
  const { setSelection, setMode } = useAppStore.getState();
  setSelection(definitionId);
  if (definitionId === null) {
    setMode({ kind: "idle" });
  }
}

export async function pasteDefinitionFromClipboard(): Promise<void> {
  const { definitionClipboard, activeDocumentId, documents, updateMeta, setSelection } = useAppStore.getState();
  if (!definitionClipboard) {
    throw new Error("Definition clipboard is empty");
  }
  if (!activeDocumentId) {
    throw new Error("No active document");
  }
  const activeDoc = documents[activeDocumentId];
  if (!activeDoc) {
    throw new Error(`Active document not found: ${activeDocumentId}`);
  }
  if (!activeDoc.meta) {
    throw new Error(`Active document has no meta: ${activeDocumentId}`);
  }
  const pastedId = uuidv4();
  const pastedDefinition = deepCloneDefinition(definitionClipboard.definition);
  updateMeta((draft) => {
    draft.definitions[pastedId] = pastedDefinition;
  }, {
    label: "Paste definition",
    forceNewEntry: true,
  });
  setSelection(pastedId);
}
