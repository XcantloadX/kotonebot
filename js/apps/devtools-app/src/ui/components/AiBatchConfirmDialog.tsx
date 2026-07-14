import React, { useState } from "react";
import { Button, Classes, Dialog, Intent, ProgressBar } from "@blueprintjs/core";
import { useTranslation } from "react-i18next";

export interface BatchDefItem {
  definitionId: string;
  hasTemplate: boolean;
}

export interface AiBatchConfirmDialogProps {
  isOpen: boolean;
  definitions: BatchDefItem[];
  onClose: () => void;
  onConfirm: () => Promise<void>;
}

export const AiBatchConfirmDialog: React.FC<AiBatchConfirmDialogProps> = ({
  isOpen,
  definitions,
  onClose,
  onConfirm,
}) => {
  const { t } = useTranslation();
  const [running, setRunning] = useState(false);

  const handleConfirm = async () => {
    setRunning(true);
    try {
      await onConfirm();
    } finally {
      setRunning(false);
    }
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={running ? undefined : onClose}
      title={t('menuItem.aiInferBatch')}
      style={{ width: 500 }}
    >
      <div className={Classes.DIALOG_BODY}>
        <p style={{ margin: "0 0 12px 0", color: "#5c7080", fontSize: 13 }}>
          {t('ai.batchConfirmDesc', { count: definitions.length })}
        </p>
        <table style={{ width: "100%", fontSize: 13, borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ borderBottom: "1px solid #d0d7e2" }}>
              <th style={{ padding: "6px 8px", textAlign: "left", fontWeight: 600 }}>{t('ai.batchTableId')}</th>
              <th style={{ padding: "6px 8px", textAlign: "left", fontWeight: 600 }}>{t('ai.batchTableTemplate')}</th>
            </tr>
          </thead>
          <tbody>
            {definitions.map((d, i) => (
              <tr key={d.definitionId} style={{ borderBottom: i < definitions.length - 1 ? "1px solid #f0f2f5" : "none" }}>
                <td style={{ padding: "6px 8px", fontFamily: "monospace", fontSize: 12 }}>
                  {d.definitionId.substring(0, 8)}...
                </td>
                <td style={{ padding: "6px 8px" }}>
                  {d.hasTemplate ? (
                    <span style={{ color: "#238551", fontSize: 12 }}>{t('ai.batchHasTemplate')}</span>
                  ) : (
                    <span style={{ color: "#8a9ba8", fontSize: 12 }}>{t('ai.batchNoTemplate')}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {running && (
          <div style={{ marginTop: 12 }}>
            <ProgressBar intent={Intent.PRIMARY} />
            <p style={{ fontSize: 12, color: "#8a9ba8", marginTop: 6 }}>
              {t('ai.inferring')}
            </p>
          </div>
        )}
      </div>
      <div className={Classes.DIALOG_FOOTER}>
        <div className={Classes.DIALOG_FOOTER_ACTIONS}>
          <Button onClick={onClose} disabled={running}>
            {t('dialog.cancel')}
          </Button>
          <Button intent={Intent.PRIMARY} onClick={handleConfirm} loading={running}>
            {t('ai.batchConfirmButton')}
          </Button>
        </div>
      </div>
    </Dialog>
  );
};
