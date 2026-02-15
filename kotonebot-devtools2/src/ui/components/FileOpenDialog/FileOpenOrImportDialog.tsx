import React, { useCallback, useEffect, useState } from "react";
import { Dialog } from "@blueprintjs/core";
import { FileOpenDialogBaseProps, FileOpenDialogContent } from "./FileOpenDialogContent";

export interface FileOpenOrImportDialogProps extends FileOpenDialogBaseProps {
  onImportDrop: (files: File[]) => boolean | Promise<boolean>;
}

export const FileOpenOrImportDialog: React.FC<FileOpenOrImportDialogProps> = ({
  isOpen,
  onClose,
  onSelect,
  onImportDrop,
  title = "Open File",
  filter,
  multiSelect = true,
}) => {
  const [isDragActive, setIsDragActive] = useState(false);

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
        <div style={{ fontSize: 14, fontWeight: 500 }}>Drag files here to import</div>
        <div style={{ fontSize: 12 }}>or press Ctrl+V to import from clipboard</div>
      </div>
    </div>
  );

  return (
    <Dialog isOpen={isOpen} onClose={onClose} title={title} style={{ width: 1240 }}>
      <FileOpenDialogContent
        isOpen={isOpen}
        onClose={onClose}
        onSelect={onSelect}
        filter={filter}
        multiSelect={multiSelect}
        rightPanel={renderImportPanel()}
      />
    </Dialog>
  );
};
