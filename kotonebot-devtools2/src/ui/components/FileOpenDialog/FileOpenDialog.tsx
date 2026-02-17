import React from "react";
import { Dialog } from "@blueprintjs/core";
import { FileOpenDialogBaseProps, FileOpenDialogContent } from "./FileOpenDialogContent";

export interface FileOpenDialogProps extends FileOpenDialogBaseProps {}

export const FileOpenDialog: React.FC<FileOpenDialogProps> = ({
  isOpen,
  onClose,
  onSelect,
  title = "Open File",
  filter,
  multiSelect = true,
}) => {
  return (
    <Dialog isOpen={isOpen} onClose={onClose} title={title} style={{ width: 900 }}>
      <FileOpenDialogContent
        isOpen={isOpen}
        onClose={onClose}
        onSelect={onSelect}
        filter={filter}
        multiSelect={multiSelect}
      />
    </Dialog>
  );
};
