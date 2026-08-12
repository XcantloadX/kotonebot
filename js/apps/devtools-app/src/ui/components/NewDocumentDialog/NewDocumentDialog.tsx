import React, { useCallback, useEffect, useId, useRef, useState } from "react";
import { Button, Classes, Dialog, InputGroup, NonIdealState, Tooltip } from "@blueprintjs/core";
import { useTranslation } from "react-i18next";
import { suggestDocumentPath } from "../../../api/ai";
import { createDocument } from "../../../api/fs";
import { usePreferencesStore } from "../../../preferences/preferencesStore";
import { useProjectInfoStore } from "../../../app/projectInfoStore";
import { useShortcut } from "../../../shortcuts/shortcutManager";
import { toaster } from "../../toaster";
import { ShortcutButton } from "../ShortcutButton";
import { DeviceCaptureDialog } from "../FileOpenDialog/DeviceCaptureDialog";
import { FileOpenDialogContent, FileOpenDialogContentHandle } from "../FileOpenDialog/FileOpenDialogContent";

type ImageSourceKind = "file" | "clipboard" | "device" | null;
type Step = "selectImage" | "saveLocation";

const FILE_FILTER = (name: string) =>
  name.endsWith(".png") || name.endsWith(".jpg") || name.endsWith(".jpeg") || name.endsWith(".bmp") || name.endsWith(".webp");

interface NewDocumentDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (targetPath: string) => Promise<void>;
}

async function readImageFromClipboard(): Promise<File | null> {
  try {
    const items = await navigator.clipboard.read();
    for (const item of items) {
      for (const type of item.types) {
        if (type.startsWith("image/")) {
          const blob = await item.getType(type);
          const ext = type === "image/png" ? "png" : "jpg";
          return new File([blob], `clipboard.${ext}`, { type });
        }
      }
    }
  } catch {
  }
  return null;
}

export const NewDocumentDialog: React.FC<NewDocumentDialogProps> = ({ isOpen, onClose, onConfirm }) => {
  const { t } = useTranslation();
  const { ai } = usePreferencesStore();
  const resourceRoot = useProjectInfoStore((state) => state.data?.resource_root ?? "");
  const shortcutInstanceId = useId();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const fileBrowserRef = useRef<FileOpenDialogContentHandle>(null);

  const [step, setStep] = useState<Step>("selectImage");

  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreviewUrl, setImagePreviewUrl] = useState<string | null>(null);
  const [sourceKind, setSourceKind] = useState<ImageSourceKind>(null);

  const [targetDir, setTargetDir] = useState("");
  const [targetFilename, setTargetFilename] = useState("");

  const [isSuggesting, setIsSuggesting] = useState(false);
  const [pendingSuggestion, setPendingSuggestion] = useState<{ suggestedDir: string; suggestedFilename: string; reason: string } | null>(null);
  const [isResultDialogOpen, setIsResultDialogOpen] = useState(false);
  const [isDeviceDialogOpen, setDeviceDialogOpen] = useState(false);

  const handleSourceFile = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      setImageFile(file);
      setImagePreviewUrl(url);
      setSourceKind("file");
      setPendingSuggestion(null);
      setIsResultDialogOpen(false);
    }
  }, []);

  const handleSourceClipboard = useCallback(async () => {
    const file = await readImageFromClipboard();
    if (file) {
      const url = URL.createObjectURL(file);
      setImageFile(file);
      setImagePreviewUrl(url);
      setSourceKind("clipboard");
      setPendingSuggestion(null);
    } else {
      toaster.show({ message: t("newDocument.noClipboardImage"), intent: "warning" });
    }
  }, [t]);

  const handleSourceDevice = useCallback(() => {
    setDeviceDialogOpen(true);
  }, []);

  const handleDeviceImport = useCallback(async (files: File[]) => {
    if (files.length > 0) {
      const file = files[0];
      const url = URL.createObjectURL(file);
      setImageFile(file);
      setImagePreviewUrl(url);
      setSourceKind("device");
      setPendingSuggestion(null);
    }
    return true;
  }, []);

  const handleNavigate = useCallback((path: string) => {
    let normalized = path.replace(/\\/g, '/').replace(/^\.\//, '');
    if (!resourceRoot) {
      setTargetDir(normalized === '.' ? '' : normalized);
      return;
    }
    const root = resourceRoot.replace(/\\/g, '/').replace(/^\.\//, '').replace(/\/$/, '');
    if (normalized === '.' || normalized === root) {
      setTargetDir('');
    } else if (normalized.startsWith(root + '/')) {
      setTargetDir(normalized.slice(root.length + 1));
    } else {
      setTargetDir(normalized);
    }
  }, [resourceRoot]);

  useEffect(() => {
    if (isOpen) {
      setStep("selectImage");
      setImageFile(null);
      setImagePreviewUrl(null);
      setSourceKind(null);
      setTargetDir("");
      setTargetFilename("");
      setPendingSuggestion(null);
      setIsResultDialogOpen(false);
    }
  }, [isOpen]);

  const handleSuggest = useCallback(async () => {
    if (!imageFile) {
      toaster.show({ message: t("newDocument.selectImageFirst"), intent: "warning" });
      return;
    }
    if (!ai.providerType || !ai.apiKey) {
      toaster.show({ message: t("newDocument.configureAiFirst"), intent: "warning" });
      return;
    }
    setIsSuggesting(true);
    try {
      const result = await suggestDocumentPath(imageFile);
      setPendingSuggestion(result);
      setIsResultDialogOpen(true);
    } catch (e: any) {
      toaster.show({ message: e?.message ?? String(e), intent: "danger" });
    } finally {
      setIsSuggesting(false);
    }
  }, [imageFile, ai, t]);

  const handleConfirm = useCallback(async () => {
    if (!imageFile || !targetFilename) {
      return;
    }
    const relativePath = targetDir ? `${targetDir}/${targetFilename}` : targetFilename;
    const targetPath = resourceRoot ? `${resourceRoot}/${relativePath}` : relativePath;
    try {
      const result = await createDocument(targetPath, imageFile);
      await onConfirm(result.imagePath);
      onClose();
    } catch (e: any) {
      toaster.show({ message: e?.message ?? String(e), intent: "danger" });
    }
  }, [imageFile, targetDir, targetFilename, resourceRoot, onConfirm, onClose]);

  const handleNext = useCallback(() => {
    if (imageFile) {
      setStep("saveLocation");
    }
  }, [imageFile]);

  const handleBack = useCallback(() => {
    setStep("selectImage");
  }, []);

  const handleAcceptSuggestion = useCallback(() => {
    if (!pendingSuggestion) return;
    if (pendingSuggestion.suggestedDir !== undefined) {
      setTargetDir(pendingSuggestion.suggestedDir);
      const navigatePath = resourceRoot
        ? `${resourceRoot}/${pendingSuggestion.suggestedDir}`.replace(/\/+$/, '')
        : pendingSuggestion.suggestedDir || '.';
      fileBrowserRef.current?.navigateTo(navigatePath);
    }
    if (pendingSuggestion.suggestedFilename) {
      setTargetFilename(pendingSuggestion.suggestedFilename);
    }
    setPendingSuggestion(null);
    setIsResultDialogOpen(false);
  }, [pendingSuggestion, resourceRoot]);

  const handleRejectSuggestion = useCallback(() => {
    setPendingSuggestion(null);
    setIsResultDialogOpen(false);
  }, []);

  useShortcut({
    id: `new-doc-enter-${shortcutInstanceId}`,
    combo: "enter",
    scope: "modal",
    when: () => {
      if (!isOpen) return false;
      if (step === "selectImage") return !!imageFile;
      if (step === "saveLocation") return !!imageFile && !!targetFilename;
      return false;
    },
    onKeyDown: () => {
      if (step === "selectImage") {
        handleNext();
      } else {
        void handleConfirm();
      }
    },
  });

  const canSuggest = !!imageFile && !!ai.providerType && !!ai.apiKey;
  const canConfirm = !!imageFile && !!targetFilename;

  const stepNumber = step === "selectImage" ? "1" : "2";

  return (
    <>
      <Dialog
        isOpen={isOpen}
        onClose={onClose}
        style={{ width: 750 }}
        canOutsideClickClose={false}
        title={
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: "#5c7080", background: "#e1e8ed", borderRadius: 3, padding: "1px 6px" }}>
              {stepNumber}/2
            </span>
            <span style={{ fontSize: 14 }}>
              {step === "selectImage" ? t("newDocument.stepSelectImage") : t("newDocument.stepSaveLocation")}
            </span>
          </div>
        }
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/bmp,image/webp"
          style={{ display: "none" }}
          onChange={handleFileInputChange}
        />

        {step === "selectImage" && (
          <div className={Classes.DIALOG_BODY}>
            <div style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 20,
              padding: "24px 0",
            }}>
              <div style={{
                width: 320,
                height: 280,
                border: "1px solid #d1d8e0",
                borderRadius: 4,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                background: "#f5f8fa",
                overflow: "hidden",
              }}>
                {imagePreviewUrl ? (
                  <img
                    src={imagePreviewUrl}
                    alt="Preview"
                    style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }}
                  />
                ) : (
                  <NonIdealState icon="media" title={t("newDocument.noImage")} />
                )}
              </div>
              <div style={{ display: "flex", gap: 12 }}>
                <Button icon="folder-open" onClick={handleSourceFile} variant="minimal" large>
                  {t("newDocument.fromFile")}
                </Button>
                <Button icon="clipboard" onClick={handleSourceClipboard} variant="minimal" large>
                  {t("newDocument.fromClipboard")}
                </Button>
                <Button icon="mobile-phone" onClick={handleSourceDevice} variant="minimal" large>
                  {t("newDocument.fromDevice")}
                </Button>
              </div>
            </div>
          </div>
        )}

        {step === "saveLocation" && (
          <>
            <div className={Classes.DIALOG_BODY} style={{ padding: 0 }}>
              <FileOpenDialogContent
                ref={fileBrowserRef}
                isOpen={isOpen}
                onClose={onClose}
                onSelect={() => {}}
                filter={FILE_FILTER}
                multiSelect={false}
                onNavigate={handleNavigate}
                hideFooter
                embedded
                browserHeight={340}
              />
            </div>
            <div style={{
              padding: "8px 16px",
              borderTop: "1px solid #d1d8e0",
              display: "flex",
              gap: 12,
              alignItems: "center",
              background: "#f7fafc",
            }}>
              <InputGroup
                value={targetFilename}
                onChange={(e) => setTargetFilename(e.target.value)}
                placeholder={t("newDocument.filenamePlaceholder")}
                fill
              />
              <Tooltip
                content={canSuggest ? t("newDocument.aiSuggestHint") : t("newDocument.aiSuggestTooltip")}
                placement="top"
              >
                <Button
                  icon="clean"
                  intent="primary"
                  onClick={handleSuggest}
                  disabled={!canSuggest || isSuggesting}
                  loading={isSuggesting}
                  variant="minimal"
                >
                  {t("newDocument.aiSuggest")}
                </Button>
              </Tooltip>
            </div>
          </>
        )}

        <div className={Classes.DIALOG_FOOTER}>
          <div className={Classes.DIALOG_FOOTER_ACTIONS}>
            <ShortcutButton onClick={onClose} shortcutText="Esc">
              {t("dialog.cancel")}
            </ShortcutButton>
            <div style={{ flex: 1 }} />
            {step === "saveLocation" && (
              <Button onClick={handleBack}>
                {t("dialog.back")}
              </Button>
            )}
            {step === "selectImage" ? (
              <ShortcutButton
                intent="primary"
                onClick={handleNext}
                disabled={!imageFile}
                shortcutText={imageFile ? "Enter" : undefined}
                rightIcon="arrow-right"
              >
                {t("dialog.next")}
              </ShortcutButton>
            ) : (
              <ShortcutButton
                intent="primary"
                onClick={handleConfirm}
                disabled={!canConfirm}
                shortcutText={canConfirm ? "Enter" : undefined}
              >
                {t("newDocument.confirm")}
              </ShortcutButton>
            )}
          </div>
        </div>
      </Dialog>

      <Dialog
        isOpen={isResultDialogOpen}
        onClose={handleRejectSuggestion}
        title={t("newDocument.aiSuggestResultTitle")}
        style={{ width: 460 }}
        canOutsideClickClose={false}
      >
        <div className={Classes.DIALOG_BODY}>
          {pendingSuggestion && (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#5c7080", marginBottom: 4 }}>{t("newDocument.saveLocation")}</div>
                <InputGroup value={pendingSuggestion.suggestedDir} readOnly fill />
              </div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#5c7080", marginBottom: 4 }}>{t("newDocument.filename")}</div>
                <InputGroup value={pendingSuggestion.suggestedFilename} readOnly fill />
              </div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#5c7080", marginBottom: 4 }}>{t("newDocument.aiSuggestReason")}</div>
                <div style={{
                  padding: 8,
                  background: "#f5f8fa",
                  borderRadius: 4,
                  fontSize: 13,
                  color: "#394b59",
                  lineHeight: 1.5,
                }}>
                  {pendingSuggestion.reason}
                </div>
              </div>
            </div>
          )}
        </div>
        <div className={Classes.DIALOG_FOOTER}>
          <div className={Classes.DIALOG_FOOTER_ACTIONS}>
            <Button onClick={handleRejectSuggestion}>{t("newDocument.aiSuggestReject")}</Button>
            <Button intent="primary" onClick={handleAcceptSuggestion}>{t("newDocument.aiSuggestAccept")}</Button>
          </div>
        </div>
      </Dialog>

      <DeviceCaptureDialog
        isOpen={isDeviceDialogOpen}
        onClose={() => setDeviceDialogOpen(false)}
        onImport={handleDeviceImport}
      />
    </>
  );
};
