import { useCallback, useEffect, useState } from "react";
import { useMessageBox } from "../ui/messageBox";
import {
  closeActiveDocumentWithChecks as closeActiveDocumentWithChecksAction,
  closeAllDocumentsWithChecks as closeAllDocumentsWithChecksAction,
  closeDocumentWithChecks as closeDocumentWithChecksAction,
  closeDocumentsWithChecks as closeDocumentsWithChecksAction,
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
  selectImages: (paths: string[]) => Promise<void>;
  saveDocument: () => Promise<void>;
  createVariantDocument: () => Promise<string | null>;
  selectVariantImage: (paths: string[], variant: string) => Promise<void>;
  importVariantImage: (files: File[], variant: string) => Promise<boolean>;
  closeDocumentWithChecks: (id: string) => Promise<boolean>;
  closeActiveDocumentWithChecks: () => Promise<boolean>;
  closeDocumentsWithChecks: (ids: string[]) => Promise<boolean>;
  closeAllDocumentsWithChecks: () => Promise<boolean>;
}

export function useEditorCommands(): EditorCommandsResult {
  const { activeDocumentId, documents } = useAppStore();
  const messageBox = useMessageBox();
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
      await openImagesWithChecks(paths, messageBox);
    },
    [messageBox]
  );

  const saveDocument = useCallback(async () => {
    await saveActiveDocumentWithToast();
  }, []);

  const createVariantDocument = useCallback(async (): Promise<string | null> => {
    return pickVariantForActiveDocument(messageBox, projectVariants);
  }, [messageBox, projectVariants]);

  const selectVariantImage = useCallback(
    async (paths: string[], variant: string): Promise<void> => {
      await selectVariantImageForActiveDocument(messageBox, paths, variant);
    },
    [messageBox]
  );

  const importVariantImage = useCallback(
    async (files: File[], variant: string): Promise<boolean> => {
      return importVariantImageForActiveDocument(messageBox, files, variant);
    },
    [messageBox]
  );

  const closeDocumentWithChecks = useCallback(
    async (id: string): Promise<boolean> => {
      return closeDocumentWithChecksAction(messageBox, id);
    },
    [messageBox]
  );

  const closeDocumentsWithChecks = useCallback(
    async (ids: string[]): Promise<boolean> => {
      return closeDocumentsWithChecksAction(messageBox, ids);
    },
    [messageBox]
  );

  const closeActiveDocumentWithChecks = useCallback(async (): Promise<boolean> => {
    return closeActiveDocumentWithChecksAction(messageBox);
  }, [messageBox]);

  const closeAllDocumentsWithChecks = useCallback(async (): Promise<boolean> => {
    return closeAllDocumentsWithChecksAction(messageBox);
  }, [messageBox]);

  return {
    canSave: !!activeMeta,
    canCreateVariantDocument: !!activeDoc?.meta,
    selectImages,
    saveDocument,
    createVariantDocument,
    selectVariantImage,
    importVariantImage,
    closeDocumentWithChecks,
    closeActiveDocumentWithChecks,
    closeDocumentsWithChecks,
    closeAllDocumentsWithChecks,
  };
}
