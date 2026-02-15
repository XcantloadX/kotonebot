import { useCallback, useEffect, useState } from "react";
import { getProjectInfo, readText } from "../api/fs";
import { cloneVariantToImage } from "../api/metaIndex";
import { useAppStore } from "./state";
import { toaster } from "../ui/toaster";
import { useMessageBox } from "../ui/messageBox";

export interface EditorCommandsResult {
  canSave: boolean;
  canCreateVariantDocument: boolean;
  isImageDialogOpen: boolean;
  isVariantImageDialogOpen: boolean;
  variantDialogTitle: string;
  openImageDialog: () => void;
  closeImageDialog: () => void;
  selectImages: (paths: string[]) => Promise<void>;
  saveDocument: () => Promise<void>;
  createVariantDocument: () => void;
  closeVariantDialog: () => void;
  selectVariantImage: (paths: string[]) => Promise<void>;
}

export function useEditorCommands(): EditorCommandsResult {
  const { activeDocumentId, documents, openDocument, setActiveMeta, saveActiveDocument } = useAppStore();
  const messageBox = useMessageBox();
  const activeDoc = activeDocumentId ? documents[activeDocumentId] : null;
  const activeMeta = activeDoc?.meta;

  const [isImageDialogOpen, setImageDialogOpen] = useState(false);
  const [isVariantImageDialogOpen, setVariantImageDialogOpen] = useState(false);
  const [pendingVariant, setPendingVariant] = useState<string | null>(null);
  const [projectVariants, setProjectVariants] = useState<string[]>([]);

  useEffect(() => {
    (async () => {
      try {
        const info = await getProjectInfo();
        setProjectVariants(info.resource_variants || []);
      } catch {
        setProjectVariants([]);
      }
    })();
  }, []);

  const openImageDialog = useCallback(() => {
    setImageDialogOpen(true);
  }, []);

  const closeImageDialog = useCallback(() => {
    setImageDialogOpen(false);
  }, []);

  const openImageWithMeta = useCallback(
    async (path: string) => {
      const img = new Image();
      img.src = `/api/image?path=${encodeURIComponent(path)}`;
      await new Promise<void>((resolve, reject) => {
        img.onload = () => resolve();
        img.onerror = () => reject(new Error(`Failed to load image: ${path}`));
      });
      openDocument(path, img.width, img.height);
      const metaPath = path + ".json";
      const content = await readText(metaPath);
      const data = JSON.parse(content);
      if (data.version !== 2) {
        throw new Error(`Unsupported meta version: ${data.version}`);
      }
      setActiveMeta(path, data);
    },
    [openDocument, setActiveMeta]
  );

  const selectImages = useCallback(
    async (paths: string[]) => {
      for (const path of paths) {
        const img = new Image();
        img.src = `/api/image?path=${encodeURIComponent(path)}`;
        await new Promise((resolve, reject) => {
          img.onload = resolve;
          img.onerror = reject;
        });

        openDocument(path, img.width, img.height);

        const metaPath = path + ".json";
        try {
          const content = await readText(metaPath);
          const data = JSON.parse(content);
          if (data.version === 2) {
            setActiveMeta(path, data);
          } else {
            const shouldStartFreshV2 = await messageBox.yes_no({
              title: "Legacy Meta Format",
              content: `Detected legacy or unknown meta format:\n${metaPath}\n\nStart fresh with V2 definitions?`,
              yesText: "Start Fresh V2",
              noText: "Cancel",
              yesIntent: "warning",
            });
            if (!shouldStartFreshV2) {
              continue;
            }
            setActiveMeta(path, { version: 2, definitions: {} });
          }
        } catch {
          setActiveMeta(path, { version: 2, definitions: {} });
        }
      }
      setImageDialogOpen(false);
    },
    [messageBox, openDocument, setActiveMeta]
  );

  const saveDocument = useCallback(async () => {
    try {
      await saveActiveDocument();
      toaster.show({ message: "Saved", intent: "success" });
    } catch {
      toaster.show({ message: "Failed to save", intent: "danger" });
    }
  }, [saveActiveDocument]);

  const createVariantDocument = useCallback(async () => {
    if (!activeDoc?.meta) {
      throw new Error("No active meta document");
    }
    if (projectVariants.length === 0) {
      toaster.show({ message: "resource_variants is not configured", intent: "warning" });
      return;
    }
    const variant = await messageBox.select({
      title: "Select Variant",
      options: projectVariants,
      defaultValue: projectVariants[0],
      confirmText: "OK",
      cancelText: "Cancel",
      confirmIntent: "primary",
      cancelIntent: "none",
    });
    if (variant === null) {
      return;
    }
    setPendingVariant(variant);
    setVariantImageDialogOpen(true);
  }, [activeDoc, messageBox, projectVariants]);

  const closeVariantDialog = useCallback(() => {
    setVariantImageDialogOpen(false);
    setPendingVariant(null);
  }, []);

  const selectVariantImage = useCallback(
    async (paths: string[]) => {
      if (!activeDoc?.meta) {
        throw new Error("No active source meta document");
      }
      if (!pendingVariant) {
        throw new Error("No pending variant selected");
      }
      if (paths.length !== 1) {
        throw new Error("Variant image clone requires single target image");
      }
      const targetImagePath = paths[0];
      try {
        await cloneVariantToImage({
          sourceMetaPath: activeDoc.meta.path,
          targetImagePath,
          variant: pendingVariant,
          forceOverwrite: false,
        });
      } catch (e: any) {
        const message = e?.message ?? String(e);
        if (message.includes("Target meta already exists")) {
          const confirmed = await messageBox.confirm_cancel({
            title: "Overwrite Existing Meta?",
            content: "Target meta already exists. Overwrite all definitions? Existing data will be lost.",
            confirmText: "Overwrite",
            cancelText: "Cancel",
            confirmIntent: "danger",
            cancelIntent: "none",
          });
          if (!confirmed) {
            setVariantImageDialogOpen(false);
            setPendingVariant(null);
            return;
          }
          await cloneVariantToImage({
            sourceMetaPath: activeDoc.meta.path,
            targetImagePath,
            variant: pendingVariant,
            forceOverwrite: true,
          });
        } else {
          throw e;
        }
      }
      await openImageWithMeta(targetImagePath);
      toaster.show({ message: `Variant document created: ${pendingVariant}`, intent: "success" });
      setVariantImageDialogOpen(false);
      setPendingVariant(null);
    },
    [activeDoc, messageBox, openImageWithMeta, pendingVariant]
  );

  return {
    canSave: !!activeMeta,
    canCreateVariantDocument: !!activeDoc?.meta,
    isImageDialogOpen,
    isVariantImageDialogOpen,
    variantDialogTitle: pendingVariant ? `Select target image for variant ${pendingVariant}` : "Select target image for variant",
    openImageDialog,
    closeImageDialog,
    selectImages,
    saveDocument,
    createVariantDocument,
    closeVariantDialog,
    selectVariantImage,
  };
}
