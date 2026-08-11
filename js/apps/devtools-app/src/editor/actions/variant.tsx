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
import { getActiveDocumentId } from "../commands/selectors";
import { openStrict } from "./image";
import { useProjectInfoStore } from "../../app/projectInfoStore";
import { useSettingsStore } from "../settings";
import i18n from "../../i18n";

export async function loadProjectVariants(): Promise<string[]> {
  const variants = useProjectInfoStore.getState().data?.variant?.variants ?? [];
  return variants;
}

export async function pickVariantForActiveDocument(
  projectVariants: string[]
): Promise<string | null> {
  const activeId = getActiveDocumentId();
  const activeDoc = activeId ? useAppStore.getState().documents[activeId] : null;
  if (!activeDoc?.meta) {
    throw new Error("No active meta document");
  }
  if (projectVariants.length === 0) {
    toaster.show({ message: i18n.t('variant.noVariantsConfigured'), intent: "warning" });
    return null;
  }
  return quickPick.select({
    title: i18n.t('variant.selectVariant'),
    placeholder: i18n.t('variant.typeVariantName'),
    options: projectVariants,
    defaultValue: projectVariants[0],
    emptyText: i18n.t('variant.noVariantMatch'),
  });
}

export async function selectVariantImageForActiveDocument(
  paths: string[],
  variant: string
): Promise<void> {
  const activeId = getActiveDocumentId();
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
      title: i18n.t('variant.overwriteExistingMeta'),
      content: i18n.t('variant.targetMetaExists'),
      confirmText: i18n.t('variant.overwrite'),
      cancelText: i18n.t('dialog.cancel'),
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
  await openStrict(targetImagePath);
  toaster.show({ message: i18n.t('variant.variantDocumentCreated', { variant }), intent: "success" });
}

export async function importVariantImageForActiveDocument(
  files: File[],
  variant: string
): Promise<boolean> {
  const activeId = getActiveDocumentId();
  const activeDoc = activeId ? useAppStore.getState().documents[activeId] : null;
  if (!activeDoc?.meta) {
    throw new Error("No active source meta document");
  }
  if (files.length === 0) {
    throw new Error("No import file selected");
  }
  if (files.length > 1) {
    toaster.show({ message: i18n.t('variant.onlyOneFileImport'), intent: "danger" });
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
      title: i18n.t('variant.confirmImportTarget'),
      content: (
        <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 760 }}>
          <div style={{ fontWeight: 600 }}>{i18n.t('variant.importVariantImageTo')}</div>
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
            <div style={{ fontWeight: 600, marginBottom: 6 }}>{i18n.t('variant.willCopy')} ({copiedDefinitions.length})</div>
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
                : i18n.t('variant.none')}
            </div>
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 600, marginBottom: 6 }}>{i18n.t('variant.skipped')} ({precheck.skippedDefinitions.length})</div>
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
                : i18n.t('variant.none')}
            </div>
          </div>
        </div>
      ),
      confirmText: i18n.t('variant.import'),
      cancelText: i18n.t('dialog.cancel'),
      confirmIntent: "primary",
      cancelIntent: "none",
    });
    if (!confirmed) {
      return false;
    }
    if (copiedDefinitions.length === 0) {
      const continueWithNoCopy = await messageBox.confirm_cancel({
        title: i18n.t('variant.noDefinitionsToCopy'),
        content: i18n.t('variant.noDefinitionsWillBeCopied'),
        confirmText: i18n.t('variant.continue'),
        cancelText: i18n.t('dialog.cancel'),
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
        title: i18n.t('variant.targetImageExists'),
        content: (
          <div>
            <div>{i18n.t('variant.targetAlreadyExists')}</div>
            <div>{precheck.targetImagePath}</div>
            <div>{precheck.targetMetaPath}</div>
            <div style={{ marginTop: 8 }}>{i18n.t('variant.deleteTargetBeforeImport')}</div>
          </div>
        ),
        confirmText: i18n.t('variant.confirmDeleteAndImport'),
        cancelText: i18n.t('dialog.cancel'),
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

export async function importFromClipboardForActiveDocument(): Promise<void> {
  const { rememberedVariant } = useSettingsStore.getState();
  const projectVariants = await loadProjectVariants();
  const variant = rememberedVariant ?? await pickVariantForActiveDocument(projectVariants);
  if (variant === null) {
    return;
  }
  const clipboardData = await navigator.clipboard.read();
  for (const item of clipboardData) {
    const imageType = item.types.find((type) => type.startsWith("image/"));
    if (imageType) {
      const blob = await item.getType(imageType);
      const file = new File([blob], "clipboard.png", { type: imageType });
      await importVariantImageForActiveDocument([file], variant);
      return;
    }
  }
  toaster.show({ message: i18n.t('deviceCapture.clipboardEmpty'), intent: "warning" });
}

export async function copySelectedPrefabToVariantForActiveDocument(
  variant?: string
): Promise<void> {
  const activeId = getActiveDocumentId();
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
    title: i18n.t('variant.confirmCopyTarget'),
    content: (
      <div style={{ display: "flex", flexDirection: "column", gap: 10, maxWidth: 760 }}>
        <div style={{ fontWeight: 600 }}>
          {i18n.t('variant.copyPrefabToVariant', { name: precheck.sourceDefinitionName, variant: targetVariant })}
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
    confirmText: i18n.t('variant.copy'),
    cancelText: i18n.t('dialog.cancel'),
    confirmIntent: "primary",
    cancelIntent: "none",
  });
  if (!confirmed) {
    return;
  }

  let forceOverwrite = false;
  if (precheck.targetDefinitionExists) {
    const overwriteConfirmed = await messageBox.confirm_cancel({
      title: i18n.t('variant.overwriteExistingPrefab'),
      content: i18n.t('variant.targetVariantHasDefinition', { definitionId: precheck.sourceDefinitionId }),
      confirmText: i18n.t('variant.overwrite'),
      cancelText: i18n.t('dialog.cancel'),
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
  await openStrict(result.targetImagePath);
  toaster.show({
    message: i18n.t('variant.copiedPrefab', { name: result.definitionName, variant: targetVariant }),
    intent: "success",
  });
}
