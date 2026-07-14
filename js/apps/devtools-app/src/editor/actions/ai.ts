import { getActiveDocumentId } from "../commands/selectors";
import { useAppStore } from "../state";
import { toaster } from "../../ui/toaster";
import { Intent } from "@blueprintjs/core";
import { inferDefinitions as apiInferDefinitions } from "../../api/ai";
import type { DefinitionV3 } from "../../model/metaV2";

export async function inferSingleSelectedDefinition(): Promise<void> {
  const docId = getActiveDocumentId();
  if (!docId) throw new Error("No active document");

  const state = useAppStore.getState();
  const activeDoc = state.documents[docId];
  if (!activeDoc?.meta || !activeDoc.selection) {
    throw new Error("No selected definition");
  }

  const defId = activeDoc.selection.definitionId;
  const definition = activeDoc.meta.data.definitions[defId];
  if (!definition) {
    throw new Error("Definition not found");
  }

  const imagePath = activeDoc.image.path;
  const templateRect = definition.props.template as { kind: string; x1: number; y1: number; x2: number; y2: number } | undefined;
  const rect = templateRect && templateRect.kind === "image"
    ? { x1: templateRect.x1, y1: templateRect.y1, x2: templateRect.x2, y2: templateRect.y2 }
    : undefined;

  const result = await apiInferDefinitions(
    imagePath,
    [{ definitionId: defId, templateRect: rect }],
  );

  const inferred = result[defId];
  if (!inferred) {
    throw new Error("AI response did not include inferred properties for this definition");
  }

  const { updateMeta } = useAppStore.getState();
  updateMeta(docId, (draft) => {
    const def = draft.definitions[defId];
    if (!def) return;
    def.name = inferred.name;
    if (inferred.displayName) {
      (def as DefinitionV3 & Record<string, unknown>).displayName = inferred.displayName;
    }
    def.props.fixed = inferred.fixed;
  }, {
    label: "AI infer definition properties",
    mergeKey: `ai:infer:${defId}`,
    forceNewEntry: true,
  });

  toaster.show({
    message: `AI: ${inferred.name}`,
    intent: Intent.SUCCESS,
    timeout: 3000,
  });
}

export async function inferBatchNullNames(): Promise<void> {
  const docId = getActiveDocumentId();
  if (!docId) throw new Error("No active document");

  const state = useAppStore.getState();
  const activeDoc = state.documents[docId];
  if (!activeDoc?.meta) {
    throw new Error("Active document has no meta");
  }

  const nullNameDefs = Object.entries(activeDoc.meta.data.definitions)
    .filter(([_, def]) => def.name === null);

  if (nullNameDefs.length === 0) {
    toaster.show({
      message: "No definitions with empty name found",
      intent: Intent.PRIMARY,
      timeout: 3000,
    });
    return;
  }

  const imagePath = activeDoc.image.path;

  const requests = nullNameDefs.map(([defId, def]) => {
    const templateRect = def.props.template as { kind: string; x1: number; y1: number; x2: number; y2: number } | undefined;
    const rect = templateRect && templateRect.kind === "image"
      ? { x1: templateRect.x1, y1: templateRect.y1, x2: templateRect.x2, y2: templateRect.y2 }
      : undefined;
    return { definitionId: defId, templateRect: rect };
  });

  const result = await apiInferDefinitions(imagePath, requests);

  let updatedCount = 0;
  const { updateMeta } = useAppStore.getState();
  updateMeta(docId, (draft) => {
    for (const [defId, inferred] of Object.entries(result)) {
      const d = draft.definitions[defId];
      if (!d || d.name !== null) continue;
      d.name = inferred.name;
      if (inferred.displayName) {
        (d as DefinitionV3 & Record<string, unknown>).displayName = inferred.displayName;
      }
      d.props.fixed = inferred.fixed;
      updatedCount++;
    }
  }, {
    label: "AI batch fill",
    mergeKey: `ai:infer:batch:${docId}`,
    forceNewEntry: true,
  });

  toaster.show({
    message: `AI filled ${updatedCount} definitions`,
    intent: updatedCount > 0 ? Intent.SUCCESS : Intent.WARNING,
    timeout: 3000,
  });
}
