import { useCallback, useEffect, useState } from "react";
import {
  closeActiveDocumentWithChecks as closeActiveDocumentWithChecksAction,
  closeAllDocumentsWithChecks as closeAllDocumentsWithChecksAction,
  closeDocumentWithChecks as closeDocumentWithChecksAction,
  closeDocumentsWithChecks as closeDocumentsWithChecksAction,
  copySelectedPrefabToVariantForActiveDocument,
  importVariantImageForActiveDocument,
  loadProjectVariants,
  openImagesWithChecks,
  pickVariantForActiveDocument,
  saveActiveDocumentWithToast,
  selectVariantImageForActiveDocument,
} from "./actions";
import { useAppStore } from "./state";

export interface EditorCommandsResult {
  canSave: boolean;
  canCreateVariantDocument: boolean;
  canCopySelectedPrefabToVariant: boolean;
  selectImages: (paths: string[]) => Promise<void>;
  saveDocument: () => Promise<void>;
  createVariantDocument: () => Promise<string | null>;
  copySelectedPrefabToVariant: (variant: string) => Promise<void>;
  selectVariantImage: (paths: string[], variant: string) => Promise<void>;
  importVariantImage: (files: File[], variant: string) => Promise<boolean>;
  closeDocumentWithChecks: (id: string) => Promise<boolean>;
  closeActiveDocumentWithChecks: () => Promise<boolean>;
  closeDocumentsWithChecks: (ids: string[]) => Promise<boolean>;
  closeAllDocumentsWithChecks: () => Promise<boolean>;
}

export function useEditorCommands(): EditorCommandsResult {
  const { activeDocumentId, documents } = useAppStore();
  const activeDoc = activeDocumentId ? documents[activeDocumentId] : null;
  const activeMeta = activeDoc?.meta;
  const [projectVariants, setProjectVariants] = useState<string[]>([]);

  useEffect(() => {
    (async () => {
      try {
        setProjectVariants(await loadProjectVariants());
      } catch {
        setProjectVariants([]);
      }
    })();
  }, []);

  const selectImages = useCallback(
    async (paths: string[]) => {
      await openImagesWithChecks(paths);
    },
    []
  );

  const saveDocument = useCallback(async () => {
    await saveActiveDocumentWithToast();
  }, []);

  const createVariantDocument = useCallback(async (): Promise<string | null> => {
    return pickVariantForActiveDocument(projectVariants);
  }, [projectVariants]);

  const selectVariantImage = useCallback(
    async (paths: string[], variant: string): Promise<void> => {
      await selectVariantImageForActiveDocument(paths, variant);
    },
    []
  );

  const importVariantImage = useCallback(
    async (files: File[], variant: string): Promise<boolean> => {
      return importVariantImageForActiveDocument(files, variant);
    },
    []
  );

  const copySelectedPrefabToVariant = useCallback(
    async (variant: string): Promise<void> => {
      await copySelectedPrefabToVariantForActiveDocument(variant);
    },
    []
  );

  const closeDocumentWithChecks = useCallback(
    async (id: string): Promise<boolean> => {
      return closeDocumentWithChecksAction(id);
    },
    []
  );

  const closeDocumentsWithChecks = useCallback(
    async (ids: string[]): Promise<boolean> => {
      return closeDocumentsWithChecksAction(ids);
    },
    []
  );

  const closeActiveDocumentWithChecks = useCallback(async (): Promise<boolean> => {
    return closeActiveDocumentWithChecksAction();
  }, []);

  const closeAllDocumentsWithChecks = useCallback(async (): Promise<boolean> => {
    return closeAllDocumentsWithChecksAction();
  }, []);

  return {
    canSave: !!activeMeta,
    canCreateVariantDocument: !!activeDoc?.meta,
    canCopySelectedPrefabToVariant: !!activeDoc?.meta
      && !!activeDoc.selection
      && activeDoc.meta.data.definitions[activeDoc.selection.definitionId]?.type === "prefab",
    selectImages,
    saveDocument,
    createVariantDocument,
    copySelectedPrefabToVariant,
    selectVariantImage,
    importVariantImage,
    closeDocumentWithChecks,
    closeActiveDocumentWithChecks,
    closeDocumentsWithChecks,
    closeAllDocumentsWithChecks,
  };
}
