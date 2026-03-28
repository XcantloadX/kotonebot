import React from "react";
import { Dialog } from "@blueprintjs/core";
import { useTranslation } from "react-i18next";
import { FileOpenDialogBaseProps, FileOpenDialogContent } from "./FileOpenDialogContent";

export interface FileOpenDialogProps extends FileOpenDialogBaseProps {}

export const FileOpenDialog: React.FC<FileOpenDialogProps> = ({
  isOpen,
  onClose,
  onSelect,
  title,
  filter,
  multiSelect = true,
}) => {
  const { t } = useTranslation();
  return (
    <Dialog isOpen={isOpen} onClose={onClose} title={title ?? t('fileDialog.openFile')} style={{ width: 900 }}>
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
