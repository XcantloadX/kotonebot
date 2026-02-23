import { getProjectInfo } from "../../api/fs";
import {
  cloneVariantToImage,
  copySelectedPrefabToVariant as copySelectedPrefabToVariantApi,
  importVariantImage as importVariantImageApi,
  preCheckCopySelectedPrefabToVariant,
  preCheckVariantImportPath,
} from "../../api/metaIndex";
import { messageBox } from "../../ui/messageBox";
import { quickPick } from "../../ui/quickPick";
import { toaster } from "../../ui/toaster";
import { useSymbolIndexStore } from "../symbolIndexStore";
import { useAppStore } from "../state";
import { openImageWithMeta } from "./image";

export async function loadProjectVariants(): Promise<string[]> {
  const info = await getProjectInfo();
  const variants = info.variant?.variants ?? [];
  return variants;
}

export async function pickVariantForActiveDocument(
  projectVariants: string[]
): Promise<string | null> {
  const activeId = useAppStore.getState().activeDocumentId;
  const activeDoc = activeId ? useAppStore.getState().documents[activeId] : null;
  if (!activeDoc?.meta) {
    throw new Error("No active meta document");
  }
  if (projectVariants.length === 0) {
    toaster.show({ message: "No selectable variants configured", intent: "warning" });
    return null;
  }
  return quickPick.select({
    title: "Select Variant",
    placeholder: "Type variant name",
    options: projectVariants,
    defaultValue: projectVariants[0],
    emptyText: "No variant match",
  });
}

export async function selectVariantImageForActiveDocument(
  paths: string[],
  variant: string
): Promise<void> {
  const activeId = useAppStore.getState().activeDocumentId;
  const activeDoc = activeId ? useAppStore.getState().documents[activeId] : null;
  if (!activeDoc?.meta) {
    throw new Error("No active source meta document");
  }
  if (paths.length !== 1) {
    throw new Error("Variant image clone requires single target image");
  }
  const targetImagePath = paths[0];
  try {
    await cloneVariantToImage({
      sourceMetaPath: activeDoc.meta.path,
      targetImagePath,
      variant,
      forceOverwrite: false,
    });
  } catch (e: any) {
    const message = e?.message ?? String(e);
    if (!message.includes("Target meta already exists")) {
      throw e;
    }
    const confirmed = await messageBox.confirm_cancel({
      title: "Overwrite Existing Meta?",
      content: "Target meta already exists. Overwrite all definitions? Existing data will be lost.",
      confirmText: "Overwrite",
      cancelText: "Cancel",
      confirmIntent: "danger",
      cancelIntent: "none",
    });
    if (!confirmed) {
      return;
    }
    await cloneVariantToImage({
      sourceMetaPath: activeDoc.meta.path,
      targetImagePath,
      variant,
      forceOverwrite: true,
    });
  }
  await useSymbolIndexStore.getState().patchMetaPath(`${targetImagePath}.json`);
  await openImageWithMeta(targetImagePath);
  toaster.show({ message: `Variant document created: ${variant}`, intent: "success" });
}

export async function importVariantImageForActiveDocument(
  files: File[],
  variant: string
): Promise<boolean> {
  const activeId = useAppStore.getState().activeDocumentId;
  const activeDoc = activeId ? useAppStore.getState().documents[activeId] : null;
  if (!activeDoc?.meta) {
    throw new Error("No active source meta document");
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
      variant,
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
      variant,
      image: files[0],
      deleteExistingTarget,
    });
    await selectVariantImageForActiveDocument([imported.targetImagePath], variant);
    return true;
  } catch (e: any) {
    toaster.show({ message: e?.message ?? String(e), intent: "danger" });
    return false;
  }
}

export async function copySelectedPrefabToVariantForActiveDocument(
  variant?: string
): Promise<void> {
  const activeId = useAppStore.getState().activeDocumentId;
  const activeDoc = activeId ? useAppStore.getState().documents[activeId] : null;
  if (!activeDoc?.meta) {
    throw new Error("No active source meta document");
  }
  let targetVariant = variant;
  if (!targetVariant) {
    const projectVariants = await loadProjectVariants();
    const picked = await pickVariantForActiveDocument(projectVariants);
    if (!picked) {
      return;
    }
    targetVariant = picked;
  }
  const selection = activeDoc.selection;
  if (!selection) {
    throw new Error("No selected definition");
  }
  const definition = activeDoc.meta.data.definitions[selection.definitionId];
  if (!definition) {
    throw new Error(`Selected definition not found: ${selection.definitionId}`);
  }
  if (definition.type !== "prefab") {
    throw new Error("Selected definition is not a prefab");
  }

  const precheck = await preCheckCopySelectedPrefabToVariant({
    sourceMetaPath: activeDoc.meta.path,
    sourceDefinitionId: selection.definitionId,
    baseImagePath: activeDoc.image.path,
    variant: targetVariant,
  });

  const confirmed = await messageBox.confirm_cancel({
    title: "Confirm Copy Target",
    content: (
      <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 760 }}>
        <div style={{ fontWeight: 600 }}>
          Copy prefab <span style={{ color: "#106ba3" }}>{precheck.sourceDefinitionName}</span> to variant{" "}
          <span style={{ color: "#106ba3" }}>{targetVariant}</span>
        </div>
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
          <div>{precheck.targetImagePath}</div>
          <div>{precheck.targetMetaPath}</div>
        </div>
      </div>
    ),
    confirmText: "Copy",
    cancelText: "Cancel",
    confirmIntent: "primary",
    cancelIntent: "none",
  });
  if (!confirmed) {
    return;
  }

  let forceOverwrite = false;
  if (precheck.targetDefinitionExists) {
    const overwriteConfirmed = await messageBox.confirm_cancel({
      title: "Overwrite Existing Prefab?",
      content: `Target variant document already has definition '${precheck.sourceDefinitionId}'. Overwrite it?`,
      confirmText: "Overwrite",
      cancelText: "Cancel",
      confirmIntent: "danger",
      cancelIntent: "none",
    });
    if (!overwriteConfirmed) {
      return;
    }
    forceOverwrite = true;
  }

  const result = await copySelectedPrefabToVariantApi({
    sourceMetaPath: activeDoc.meta.path,
    sourceDefinitionId: selection.definitionId,
    baseImagePath: activeDoc.image.path,
    variant: targetVariant,
    forceOverwrite,
  });

  await useSymbolIndexStore.getState().patchMetaPath(result.targetMetaPath);
  await openImageWithMeta(result.targetImagePath);
  toaster.show({
    message: `Copied prefab '${result.definitionName}' to variant '${targetVariant}'`,
    intent: "success",
  });
}
