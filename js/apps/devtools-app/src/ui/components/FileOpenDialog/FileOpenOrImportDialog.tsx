import React, { useCallback, useEffect, useState } from "react";
import { Dialog, Button } from "@blueprintjs/core";
import { useTranslation } from "react-i18next";
import { FileOpenDialogBaseProps, FileOpenDialogContent } from "./FileOpenDialogContent";
import { DeviceCaptureDialog } from "./DeviceCaptureDialog";

export interface FileOpenOrImportDialogProps extends FileOpenDialogBaseProps {
  onImportDrop: (files: File[]) => boolean | Promise<boolean>;
  showDeviceCapture?: boolean;
}

export const FileOpenOrImportDialog: React.FC<FileOpenOrImportDialogProps> = ({
  isOpen,
  onClose,
  onSelect,
  onImportDrop,
  title,
  filter,
  multiSelect = true,
  showDeviceCapture = false,
}) => {
  const { t } = useTranslation();
  const [isDragActive, setIsDragActive] = useState(false);
  const [isDeviceCaptureOpen, setIsDeviceCaptureOpen] = useState(false);

  const importFromFiles = useCallback(
    async (files: FileList) => {
      if (files.length === 0) {
        return;
      }
      const shouldClose = await onImportDrop(Array.from(files));
      if (shouldClose) {
        onClose();
      }
    },
    [onClose, onImportDrop],
  );

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const handlePaste = (event: ClipboardEvent) => {
      const clipboardData = event.clipboardData;
      if (!clipboardData) {
        throw new Error("Clipboard data is missing");
      }
      if (clipboardData.files.length === 0) {
        return;
      }
      event.preventDefault();
      void importFromFiles(clipboardData.files);
    };
    window.addEventListener("paste", handlePaste);
    return () => window.removeEventListener("paste", handlePaste);
  }, [importFromFiles, isOpen]);

  const handleDrop = async (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragActive(false);
    await importFromFiles(event.dataTransfer.files);
  };

  const handlePaste = async (event: React.ClipboardEvent<HTMLDivElement>) => {
    if (event.clipboardData.files.length === 0) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    await importFromFiles(event.clipboardData.files);
  };

  const handleDragLeave = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    event.stopPropagation();
    const next = event.relatedTarget;
    if (next && event.currentTarget.contains(next as Node)) {
      return;
    }
    setIsDragActive(false);
  };

  const handleDeviceCaptureImport = useCallback(
    async (files: File[]) => {
      const shouldClose = await onImportDrop(files);
      if (shouldClose) {
        setIsDeviceCaptureOpen(false);
      }
      return shouldClose;
    },
    [onImportDrop]
  );

  const renderImportPanel = () => (
    <div
      onDragEnter={(event) => {
        event.preventDefault();
        event.stopPropagation();
        setIsDragActive(true);
      }}
      onDragOver={(event) => {
        event.preventDefault();
        event.stopPropagation();
        event.dataTransfer.dropEffect = "copy";
        setIsDragActive(true);
      }}
      onDragLeave={handleDragLeave}
      onDrop={(event) => {
        void handleDrop(event);
      }}
      onPaste={(event) => {
        void handlePaste(event);
      }}
      style={{
        height: "100%",
        border: "2px dashed #8a9ba8",
        borderRadius: 6,
        background: isDragActive ? "#ebf2f7" : "#f7fafc",
        color: "#5c7080",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 18,
      }}
      tabIndex={0}
    >
      <div style={{ textAlign: "center", display: "flex", flexDirection: "column", gap: 10, alignItems: "center" }}>
        <span className="bp5-icon bp5-icon-import" style={{ fontSize: 36 }} />
        <div style={{ fontSize: 14, fontWeight: 500 }}>{t('fileDialog.dragFilesHere')}</div>
        <div style={{ fontSize: 12 }}>{t('fileDialog.orPressCtrlV')}</div>
        {showDeviceCapture && (
          <Button
            intent="primary"
            icon="camera"
            onClick={() => setIsDeviceCaptureOpen(true)}
            style={{ marginTop: 8 }}
          >
            {t('fileDialog.captureFromDevice')}
          </Button>
        )}
      </div>
    </div>
  );

  return (
    <>
      <Dialog isOpen={isOpen} onClose={onClose} title={title ?? t('fileDialog.openFile')} style={{ width: 1240 }}>
        <FileOpenDialogContent
          isOpen={isOpen}
          onClose={onClose}
          onSelect={onSelect}
          filter={filter}
          multiSelect={multiSelect}
          rightPanel={renderImportPanel()}
        />
      </Dialog>
      <DeviceCaptureDialog
        isOpen={isDeviceCaptureOpen}
        onClose={() => setIsDeviceCaptureOpen(false)}
        onImport={handleDeviceCaptureImport}
      />
    </>
  );
};
