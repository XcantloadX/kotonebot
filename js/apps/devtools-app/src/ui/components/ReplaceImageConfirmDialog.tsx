import React from "react";
import { Button, Callout, Classes, Dialog } from "@blueprintjs/core";
import { useTranslation } from "react-i18next";

export interface DimensionMismatch {
  currentWidth: number;
  currentHeight: number;
  newWidth: number;
  newHeight: number;
}

export interface ReplaceImageConfirmDialogProps {
  isOpen: boolean;
  /** 当前文档图片的路径（用于显示标签）。 */
  currentImagePath: string;
  /** 当前文档图片的显示 URL。 */
  currentImageUrl: string;
  /** 新图片的标签（路径或文件名）。 */
  newImageLabel: string;
  /** 新图片的显示 URL（服务端路径对应 API URL，或 File 对象对应的 objectURL）。 */
  newImageUrl: string;
  /** 若新旧图片尺寸不同，传入该对象以显示警告；尺寸一致时不传。 */
  dimensionMismatch?: DimensionMismatch;
  onClose: () => void;
  onConfirm: () => void | Promise<void>;
}

export const ReplaceImageConfirmDialog: React.FC<ReplaceImageConfirmDialogProps> = ({
  isOpen,
  currentImagePath,
  currentImageUrl,
  newImageLabel,
  newImageUrl,
  dimensionMismatch,
  onClose,
  onConfirm,
}) => {
  const { t } = useTranslation();

  const imageContainerStyle: React.CSSProperties = {
    height: 320,
    background: "#e8ecf0",
    borderRadius: 3,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    overflow: "hidden",
  };

  const imageStyle: React.CSSProperties = {
    maxWidth: "100%",
    maxHeight: "100%",
    objectFit: "contain",
    display: "block",
  };

  const colHeaderStyle: React.CSSProperties = {
    fontSize: 13,
    fontWeight: 500,
    marginBottom: 8,
    color: "#394b59",
  };

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={t("image.replaceImage")}
      style={{ width: 800 }}
    >
      <div className={Classes.DIALOG_BODY}>
        <p style={{ margin: "0 0 16px 0" }}>{t("image.replaceConfirmPrompt")}</p>
        {dimensionMismatch && (
          <Callout intent="warning" compact style={{ marginBottom: 16 }}>
            {t("image.dimensionMismatch", {
              currentW: dimensionMismatch.currentWidth,
              currentH: dimensionMismatch.currentHeight,
              newW: dimensionMismatch.newWidth,
              newH: dimensionMismatch.newHeight,
            })}
          </Callout>
        )}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <div style={colHeaderStyle}>{t("image.current")}</div>
            <div style={imageContainerStyle}>
              <img src={currentImageUrl} alt="current" style={imageStyle} />
            </div>
          </div>
          <div>
            <div style={colHeaderStyle}>{t("image.new")}</div>
            <div style={imageContainerStyle}>
              <img src={newImageUrl} alt="new" style={imageStyle} />
            </div>
          </div>
        </div>
      </div>
      <div className={Classes.DIALOG_FOOTER}>
        <div className={Classes.DIALOG_FOOTER_ACTIONS}>
          <Button onClick={onClose}>{t("dialog.cancel")}</Button>
          <Button intent="danger" onClick={() => void onConfirm()}>
            {t("image.replace")}
          </Button>
        </div>
      </div>
    </Dialog>
  );
};
