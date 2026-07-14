import { v4 as uuidv4 } from "uuid";
import type { DefinitionModel } from "../../model/metaV2";
import { useAppStore } from "../state";
import { getActiveDocumentId } from "../commands/selectors";

function deepCloneDefinition(definition: DefinitionModel): DefinitionModel {
  return JSON.parse(JSON.stringify(definition)) as DefinitionModel;
}

function getActiveDefinitionOrThrow(): { docId: string; definitionId: string; definition: DefinitionModel } {
  const docId = getActiveDocumentId();
  if (!docId) {
    throw new Error("No active document");
  }
  const state = useAppStore.getState();
  const activeDoc = state.documents[docId];
  if (!activeDoc) {
    throw new Error(`Active document not found: ${docId}`);
  }
  if (!activeDoc.meta) {
    throw new Error(`Active document has no meta: ${docId}`);
  }
  if (!activeDoc.selection) {
    throw new Error("No selected definition");
  }
  const definitionId = activeDoc.selection.definitionId;
  const definition = activeDoc.meta.data.definitions[definitionId];
  if (!definition) {
    throw new Error(`Definition not found: ${definitionId}`);
  }
  return { docId, definitionId, definition };
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
  const { docId } = getActiveDefinitionOrThrow();
  const { updateMeta, setSelection } = useAppStore.getState();
  const { definition } = getActiveDefinitionOrThrow();
  const duplicatedId = uuidv4();
  const duplicatedDefinition = deepCloneDefinition(definition);
  updateMeta(docId, (draft) => {
    draft.definitions[duplicatedId] = duplicatedDefinition;
  }, {
    label: "Duplicate definition",
    forceNewEntry: true,
  });
  setSelection(docId, duplicatedId);
}

export async function deleteSelectedDefinition(): Promise<void> {
  const { docId, definitionId } = getActiveDefinitionOrThrow();
  const { updateMeta, setSelection, setMode } = useAppStore.getState();
  updateMeta(docId, (draft) => {
    delete draft.definitions[definitionId];
  }, {
    label: "Delete definition",
    mergeKey: `delete:${definitionId}`,
    forceNewEntry: true,
  });
  setSelection(docId, null);
  setMode(docId, { kind: "idle" });
}

export async function cutSelectedDefinition(): Promise<void> {
  const { docId, definitionId, definition } = getActiveDefinitionOrThrow();
  const { setDefinitionClipboard, updateMeta, setSelection, setMode } = useAppStore.getState();
  setDefinitionClipboard({
    sourceDefinitionId: definitionId,
    definition: deepCloneDefinition(definition),
  });
  updateMeta(docId, (draft) => {
    delete draft.definitions[definitionId];
  }, {
    label: "Cut definition",
    mergeKey: `cut:${definitionId}`,
    forceNewEntry: true,
  });
  setSelection(docId, null);
  setMode(docId, { kind: "idle" });
}

export async function selectDefinition(definitionId: string | null): Promise<void> {
  const docId = getActiveDocumentId();
  if (!docId) return;
  const { setSelection, setMode } = useAppStore.getState();
  setSelection(docId, definitionId);
  if (definitionId === null) {
    setMode(docId, { kind: "idle" });
  }
}

export async function pasteDefinitionFromClipboard(): Promise<void> {
  const state = useAppStore.getState();
  const docId = getActiveDocumentId();
  if (!docId) {
    throw new Error("No active document");
  }
  const { definitionClipboard, documents, updateMeta, setSelection } = state;
  if (!definitionClipboard) {
    throw new Error("Definition clipboard is empty");
  }
  const activeDoc = documents[docId];
  if (!activeDoc) {
    throw new Error(`Active document not found: ${docId}`);
  }
  if (!activeDoc.meta) {
    throw new Error(`Active document has no meta: ${docId}`);
  }
  const pastedId = uuidv4();
  const pastedDefinition = deepCloneDefinition(definitionClipboard.definition);
  updateMeta(docId, (draft) => {
    draft.definitions[pastedId] = pastedDefinition;
  }, {
    label: "Paste definition",
    forceNewEntry: true,
  });
  setSelection(docId, pastedId);
}
