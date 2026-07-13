import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { loadProjectVariants, pickVariantForActiveDocument } from "./actions/variant";
import { editorActions } from "./actions";
import { useAppStore } from "./state";
import { useSettingsStore } from "./settings";
import { FileOpenDialog } from "../ui/components/FileOpenDialog/FileOpenDialog";
import { FileOpenOrImportDialog } from "../ui/components/FileOpenDialog/FileOpenOrImportDialog";
import { DeviceCaptureDialog } from "../ui/components/FileOpenDialog/DeviceCaptureDialog";
import { ReplaceImageConfirmDialog } from "../ui/components/ReplaceImageConfirmDialog";
import { PreferencesDialog } from "../ui/PreferencesDialog";
import { NewDocumentDialog } from "../ui/components/NewDocumentDialog/NewDocumentDialog";
import { getImageUrl } from "../api/fs";
import type { ReplaceImageSource } from "./actions/image";
import { toaster } from "../ui/toaster";
import { useShortcutScope } from "../shortcuts/shortcutManager";
import type { EditorCommandContext } from "./commands/types";

async function measureImageUrl(url: string): Promise<{ width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve({ width: img.width, height: img.height });
    img.onerror = () => reject(new Error(`Failed to load image: ${url}`));
    img.src = url;
  });
}

let globalCommandContext: EditorCommandContext = { ui: {} };

export function setGlobalCommandContext(ctx: EditorCommandContext) {
  globalCommandContext = ctx;
}

export function getGlobalCommandContext(): EditorCommandContext {
  return globalCommandContext;
}

interface EditorDialogsContextValue {
  commandContext: EditorCommandContext;
}

const EditorDialogsContext = createContext<EditorDialogsContextValue | null>(null);

export function useEditorDialogsContext(): EditorDialogsContextValue {
  const ctx = useContext(EditorDialogsContext);
  if (!ctx) throw new Error("useEditorDialogsContext must be used within EditorDialogsProvider");
  return ctx;
}

export const EditorDialogsProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { t } = useTranslation();
  const { activeDocumentId, documents } = useAppStore();
  const activeDoc = activeDocumentId ? documents[activeDocumentId] : null;

  const [isImageDialogOpen, setImageDialogOpen] = useState(false);
  const [variantDialogState, setVariantDialogState] = useState<{ isOpen: boolean; variant: string | null }>({
    isOpen: false,
    variant: null,
  });
  const [deviceCaptureState, setDeviceCaptureState] = useState<{ isOpen: boolean; variant: string | null }>({
    isOpen: false,
    variant: null,
  });
  const [replaceImageDialogOpen, setReplaceImageDialogOpen] = useState(false);
  const [replaceImageSource, setReplaceImageSource] = useState<ReplaceImageSource | null>(null);
  const [replaceImageNewDims, setReplaceImageNewDims] = useState<{ width: number; height: number } | null>(null);
  const [isNewDocumentDialogOpen, setNewDocumentDialogOpen] = useState(false);
  const [isPreferencesDialogOpen, setPreferencesDialogOpen] = useState(false);

  const variantDialogTitle = variantDialogState.variant
    ? t('dialog.selectTargetImage') + ` ${variantDialogState.variant}`
    : t('dialog.selectTargetImage');
  const modalOpen = isImageDialogOpen || isNewDocumentDialogOpen || variantDialogState.isOpen || deviceCaptureState.isOpen || replaceImageDialogOpen || replaceImageSource !== null || isPreferencesDialogOpen;

  useShortcutScope("modal", modalOpen);

  const openImageDialog = useCallback(() => {
    setImageDialogOpen(true);
  }, []);

  const closeImageDialog = useCallback(() => {
    setImageDialogOpen(false);
  }, []);

  const closeVariantDialog = useCallback(() => {
    setVariantDialogState({ isOpen: false, variant: null });
  }, []);

  const openVariantDialog = useCallback(async () => {
    const { rememberedVariant } = useSettingsStore.getState();
    const projectVariants = await loadProjectVariants();
    const variant = rememberedVariant ?? await pickVariantForActiveDocument(projectVariants);
    if (variant === null) {
      return;
    }
    setVariantDialogState({ isOpen: true, variant });
  }, []);

  const openDeviceCaptureDialog = useCallback(async () => {
    const { rememberedVariant } = useSettingsStore.getState();
    const projectVariants = await loadProjectVariants();
    const variant = rememberedVariant ?? await pickVariantForActiveDocument(projectVariants);
    if (variant === null) {
      return;
    }
    setDeviceCaptureState({ isOpen: true, variant });
  }, []);

  const openReplaceImageDialog = useCallback(() => {
    setReplaceImageDialogOpen(true);
  }, []);

  const openNewDocumentDialog = useCallback(() => {
    setNewDocumentDialogOpen(true);
  }, []);

  const closeNewDocumentDialog = useCallback(() => {
    setNewDocumentDialogOpen(false);
  }, []);

  const openPreferencesDialog = useCallback(() => {
    setPreferencesDialogOpen(true);
  }, []);

  const closePreferencesDialog = useCallback(() => {
    setPreferencesDialogOpen(false);
  }, []);

  const handleNewDocumentConfirm = useCallback(async (imagePath: string) => {
    await editorActions.newDocument.openFromPath(imagePath);
  }, []);

  const handleSelectImages = useCallback(async (paths: string[]) => {
    await editorActions.image.openWithChecks(paths);
    setImageDialogOpen(false);
  }, []);

  const handleSelectVariantImage = useCallback(async (paths: string[]) => {
    const variant = variantDialogState.variant;
    if (!variant) {
      throw new Error("No variant selected for target image");
    }
    await editorActions.variant.selectImageForActive(paths, variant);
    setVariantDialogState({ isOpen: false, variant: null });
  }, [variantDialogState.variant]);

  const handleImportVariantImage = useCallback(async (files: File[]) => {
    const variant = variantDialogState.variant;
    if (!variant) {
      throw new Error("No variant selected for import");
    }
    const shouldClose = await editorActions.variant.importImageForActive(files, variant);
    if (shouldClose) {
      setVariantDialogState({ isOpen: false, variant: null });
    }
    return shouldClose;
  }, [variantDialogState.variant]);

  const handleDeviceCaptureImport = useCallback(async (files: File[]) => {
    const variant = deviceCaptureState.variant;
    if (!variant) {
      throw new Error("No variant selected for device capture");
    }
    const shouldClose = await editorActions.variant.importImageForActive(files, variant);
    if (shouldClose) {
      setDeviceCaptureState({ isOpen: false, variant: null });
    }
    return shouldClose;
  }, [deviceCaptureState.variant]);

  const handleSelectReplaceImage = useCallback(async (paths: string[]) => {
    if (paths.length !== 1) return;
    setReplaceImageDialogOpen(false);
    const path = paths[0];
    let newDims: { width: number; height: number } | null = null;
    try {
      newDims = await measureImageUrl(getImageUrl(path));
    } catch {
      // 量尺寸失败时不阻断流程，仅无法显示警告
    }
    setReplaceImageNewDims(newDims);
    setReplaceImageSource({ kind: "path", path });
  }, []);

  const handleImportReplaceImage = useCallback(async (files: File[]): Promise<boolean> => {
    if (files.length === 0) return false;
    if (files.length > 1) {
      toaster.show({ message: t("image.onlyOneFileReplace"), intent: "warning" });
      return false;
    }
    const file = files[0];
    const objectUrl = URL.createObjectURL(file);
    let newDims: { width: number; height: number } | null = null;
    try {
      newDims = await measureImageUrl(objectUrl);
    } catch {
      // 量尺寸失败时不阻断流程，仅无法显示警告
    }
    setReplaceImageNewDims(newDims);
    setReplaceImageSource({ kind: "file", file, objectUrl });
    return true;
  }, [t]);

  const handleConfirmReplace = useCallback(async () => {
    if (!replaceImageSource) return;
    try {
      await editorActions.image.replaceActive(replaceImageSource);
    } finally {
      if (replaceImageSource.kind === "file") {
        URL.revokeObjectURL(replaceImageSource.objectUrl);
      }
      setReplaceImageSource(null);
      setReplaceImageNewDims(null);
    }
  }, [replaceImageSource]);

  const handleCancelReplace = useCallback(() => {
    if (replaceImageSource?.kind === "file") {
      URL.revokeObjectURL(replaceImageSource.objectUrl);
    }
    setReplaceImageSource(null);
    setReplaceImageNewDims(null);
  }, [replaceImageSource]);

  const commandContext = useMemo<EditorCommandContext>(
    () => ({
      ui: {
        openImageDialog,
        openNewDocumentDialog,
        openVariantDialog,
        openDeviceCaptureDialog,
        openReplaceImageDialog,
        openPreferencesDialog,
      },
    }),
    [openImageDialog, openNewDocumentDialog, openVariantDialog, openDeviceCaptureDialog, openReplaceImageDialog, openPreferencesDialog],
  );

  useEffect(() => {
    setGlobalCommandContext(commandContext);
  }, [commandContext]);

  const contextValue = useMemo<EditorDialogsContextValue>(
    () => ({ commandContext }),
    [commandContext],
  );

  return (
    <EditorDialogsContext.Provider value={contextValue}>
      {children}
      <FileOpenDialog
        isOpen={isImageDialogOpen}
        onClose={closeImageDialog}
        onSelect={handleSelectImages}
        title={t('dialog.openImage')}
        filter={(name) => name.endsWith(".png")}
      />
      <FileOpenOrImportDialog
        isOpen={variantDialogState.isOpen}
        onClose={closeVariantDialog}
        onSelect={handleSelectVariantImage}
        onImportDrop={handleImportVariantImage}
        title={variantDialogTitle}
        filter={(name) => name.endsWith(".png")}
        multiSelect={false}
        showDeviceCapture={false}
      />
      <DeviceCaptureDialog
        isOpen={deviceCaptureState.isOpen}
        onClose={() => setDeviceCaptureState({ isOpen: false, variant: null })}
        onImport={handleDeviceCaptureImport}
      />
      <FileOpenOrImportDialog
        isOpen={replaceImageDialogOpen}
        onClose={() => setReplaceImageDialogOpen(false)}
        onSelect={handleSelectReplaceImage}
        onImportDrop={handleImportReplaceImage}
        title={t("image.replaceImage")}
        filter={(name) => name.endsWith(".png")}
        multiSelect={false}
        showDeviceCapture={false}
      />
      {replaceImageSource !== null && activeDoc !== null && (
        <ReplaceImageConfirmDialog
          isOpen={true}
          currentImagePath={activeDoc.image.path}
          currentImageUrl={getImageUrl(activeDoc.image.path)}
          newImageLabel={
            replaceImageSource.kind === "path"
              ? replaceImageSource.path
              : replaceImageSource.file.name
          }
          newImageUrl={
            replaceImageSource.kind === "path"
              ? getImageUrl(replaceImageSource.path)
              : replaceImageSource.objectUrl
          }
          dimensionMismatch={
            replaceImageNewDims !== null &&
            (replaceImageNewDims.width !== activeDoc.image.width ||
              replaceImageNewDims.height !== activeDoc.image.height)
              ? {
                  currentWidth: activeDoc.image.width,
                  currentHeight: activeDoc.image.height,
                  newWidth: replaceImageNewDims.width,
                  newHeight: replaceImageNewDims.height,
                }
              : undefined
          }
          onClose={handleCancelReplace}
          onConfirm={handleConfirmReplace}
        />
      )}
      <NewDocumentDialog
        isOpen={isNewDocumentDialogOpen}
        onClose={closeNewDocumentDialog}
        onConfirm={handleNewDocumentConfirm}
      />
      <PreferencesDialog
        isOpen={isPreferencesDialogOpen}
        onClose={closePreferencesDialog}
      />
    </EditorDialogsContext.Provider>
  );
};
