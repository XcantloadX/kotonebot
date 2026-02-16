import { useCallback, useEffect, useState } from "react";
import { getProjectInfo, readText } from "../api/fs";
import { cloneVariantToImage, importVariantImage as importVariantImageApi, preCheckVariantImportPath } from "../api/metaIndex";
import { useAppStore } from "./state";
import { toaster } from "../ui/toaster";
import { useMessageBox } from "../ui/messageBox";
import { useSymbolIndexStore } from "./symbolIndexStore";

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
  importVariantImage: (files: File[]) => Promise<boolean>;
  closeDocumentWithChecks: (id: string) => Promise<boolean>;
  closeActiveDocumentWithChecks: () => Promise<boolean>;
  closeDocumentsWithChecks: (ids: string[]) => Promise<boolean>;
  closeAllDocumentsWithChecks: () => Promise<boolean>;
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
        const variantNames = info.variant?.names ?? [];
        const baseVariant = info.variant?.base ?? null;
        setProjectVariants(variantNames.filter((name) => name !== baseVariant));
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
      toaster.show({ message: "No selectable variants configured", intent: "warning" });
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
      await useSymbolIndexStore.getState().patchMetaPath(`${targetImagePath}.json`);
      await openImageWithMeta(targetImagePath);
      toaster.show({ message: `Variant document created: ${pendingVariant}`, intent: "success" });
      setVariantImageDialogOpen(false);
      setPendingVariant(null);
    },
    [activeDoc, messageBox, openImageWithMeta, pendingVariant]
  );

  const importVariantImage = useCallback(
    async (files: File[]) => {
      if (!activeDoc?.meta) {
        throw new Error("No active source meta document");
      }
      if (!pendingVariant) {
        throw new Error("No pending variant selected");
      }
      if (files.length === 0) {
        throw new Error("No import file selected");
      }
      if (files.length > 1) {
        toaster.show({ message: "Only one file can be imported at a time", intent: "danger" });
        return false;
      }

      try {
        const precheck = await preCheckVariantImportPath({
          sourceMetaPath: activeDoc.meta.path,
          baseImagePath: activeDoc.image.path,
          variant: pendingVariant,
          image: files[0],
        });
        const copiedDefinitions = precheck.copiedDefinitions.map((definition) => definition.name);
        const confirmed = await messageBox.confirm_cancel({
          title: "Confirm Import Target",
          content: (
            <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 760 }}>
              <div style={{ fontWeight: 600 }}>Import variant image to</div>
              <div
                style={{
                  fontFamily: "Consolas, 'Courier New', monospace",
                  fontSize: 12,
                  background: "#f6f7f9",
                  border: "1px solid #d8e1e8",
                  borderRadius: 4,
                  padding: "8px 10px",
                  wordBreak: "break-all",
                }}
              >
                {precheck.targetImagePath}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>Will Copy ({copiedDefinitions.length})</div>
                <div
                  style={{
                    maxHeight: 150,
                    overflowY: "auto",
                    border: "1px solid #d8e1e8",
                    borderRadius: 4,
                    padding: "8px 10px",
                    background: "#f8fbff",
                    fontSize: 12,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {copiedDefinitions.length > 0
                    ? copiedDefinitions.map((name) => (
                      <div key={name} style={{ color: "#2d72d2" }}>
                        {name}
                      </div>
                    ))
                    : "None"}
                </div>
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>Skipped ({precheck.skippedDefinitions.length})</div>
                <div
                  style={{
                    maxHeight: 220,
                    overflowY: "auto",
                    border: "1px solid #d8e1e8",
                    borderRadius: 4,
                    padding: "8px 10px",
                    background: "#fff8f8",
                    fontSize: 12,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                  }}
                >
                  {precheck.skippedDefinitions.length > 0
                    ? precheck.skippedDefinitions.map((definition, index) => (
                      <div key={`${definition.definitionId}-${index}`}>
                        <span style={{ color: "#c23030" }}>{definition.name}</span>
                        <span style={{ color: "#5c7080" }}>{" : "}{definition.reason}</span>
                      </div>
                    ))
                    : "None"}
                </div>
              </div>
            </div>
          ),
          confirmText: "Import",
          cancelText: "Cancel",
          confirmIntent: "primary",
          cancelIntent: "none",
        });
        if (!confirmed) {
          return false;
        }
        if (copiedDefinitions.length === 0) {
          const continueWithNoCopy = await messageBox.confirm_cancel({
            title: "No Definitions To Copy",
            content: "No definitions will be copied. Continue import anyway?",
            confirmText: "Continue",
            cancelText: "Cancel",
            confirmIntent: "warning",
            cancelIntent: "none",
          });
          if (!continueWithNoCopy) {
            return false;
          }
        }

        const targetExists = precheck.targetImageExists || precheck.targetMetaExists;
        let deleteExistingTarget = false;
        if (targetExists) {
          const deleteConfirmed = await messageBox.confirm_cancel({
            title: "Target Image Already Exists",
            content: (
              <div>
                <div>Target already exists:</div>
                <div>{precheck.targetImagePath}</div>
                <div>{precheck.targetMetaPath}</div>
                <div style={{ marginTop: 8 }}>Delete target image and target image document before import?</div>
              </div>
            ),
            confirmText: "Delete and Import",
            cancelText: "Cancel",
            confirmIntent: "danger",
            cancelIntent: "none",
          });
          if (!deleteConfirmed) {
            return false;
          }
          deleteExistingTarget = true;
        }
        const imported = await importVariantImageApi({
          baseImagePath: activeDoc.image.path,
          variant: pendingVariant,
          image: files[0],
          deleteExistingTarget,
        });
        await selectVariantImage([imported.targetImagePath]);
        return true;
      } catch (e: any) {
        toaster.show({ message: e?.message ?? String(e), intent: "danger" });
        return false;
      }
    },
    [activeDoc, messageBox, pendingVariant, selectVariantImage]
  );

  const closeDocumentWithChecks = useCallback(
    async (id: string): Promise<boolean> => {
      const current = useAppStore.getState();
      const doc = current.documents[id];
      if (!doc) {
        throw new Error(`Document not found: ${id}`);
      }
      if (!doc.dirty) {
        current.closeDocument(id);
        return true;
      }

      const action = await messageBox.show<"save" | "dont-save" | "cancel">({
        title: "Unsaved changes",
        content: `File "${id.split(/[/\\]/).pop()}" has unsaved changes. Save before closing?`,
        buttons: [
          { value: "save", text: "Save", intent: "primary" },
          { value: "dont-save", text: "Don't Save" },
          { value: "cancel", text: "Cancel" },
        ],
        dismissValue: "cancel",
        canEscapeKeyClose: true,
        canOutsideClickClose: false,
      });

      if (action === "cancel") {
        return false;
      }
      if (action === "save") {
        current.setActiveDocument(id);
        try {
          await current.saveActiveDocument();
        } catch {
          return false;
        }
      }
      current.closeDocument(id);
      return true;
    },
    [messageBox]
  );

  const closeDocumentsWithChecks = useCallback(
    async (ids: string[]): Promise<boolean> => {
      for (const id of ids) {
        const ok = await closeDocumentWithChecks(id);
        if (!ok) {
          return false;
        }
      }
      return true;
    },
    [closeDocumentWithChecks]
  );

  const closeActiveDocumentWithChecks = useCallback(async (): Promise<boolean> => {
    const current = useAppStore.getState();
    const activeId = current.activeDocumentId;
    if (!activeId) {
      throw new Error("No active document");
    }
    return closeDocumentWithChecks(activeId);
  }, [closeDocumentWithChecks]);

  const closeAllDocumentsWithChecks = useCallback(async (): Promise<boolean> => {
    const current = useAppStore.getState();
    const ids = Object.keys(current.documents);
    return closeDocumentsWithChecks(ids);
  }, [closeDocumentsWithChecks]);

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
    importVariantImage,
    closeDocumentWithChecks,
    closeActiveDocumentWithChecks,
    closeDocumentsWithChecks,
    closeAllDocumentsWithChecks,
  };
}
