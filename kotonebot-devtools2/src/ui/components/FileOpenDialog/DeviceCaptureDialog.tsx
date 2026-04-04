import React, { useCallback, useEffect, useId, useRef, useState } from "react";
import { Button, Dialog, HTMLSelect, InputGroup, Spinner, NonIdealState } from "@blueprintjs/core";
import { useTranslation } from "react-i18next";
import { listAdbDevices, captureAdbScreenshot, AdbDevice } from "../../../api/device";
import { fetchImageAsFile } from "../../../api/fs";
import { useShortcut } from "../../../shortcuts/shortcutManager";

export interface DeviceCaptureDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onImport: (files: File[]) => boolean | Promise<boolean>;
}

export const DeviceCaptureDialog: React.FC<DeviceCaptureDialogProps> = ({
  isOpen,
  onClose,
  onImport,
}) => {
  const { t } = useTranslation();
  const [devices, setDevices] = useState<AdbDevice[]>([]);
  const [selectedSerial, setSelectedSerial] = useState<string>("");
  const [displayId, setDisplayId] = useState<string>("");
  const [isLoadingDevices, setIsLoadingDevices] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [capturedImagePath, setCapturedImagePath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const hasAutoCaptured = useRef(false);
  const shortcutInstanceId = useId();

  const loadDevices = useCallback(async () => {
    setIsLoadingDevices(true);
    setError(null);
    try {
      const result = await listAdbDevices();
      if (result.error) {
        setError(result.error);
        setDevices([]);
      } else {
        setDevices(result.devices);
        if (result.devices.length > 0 && !selectedSerial) {
          const firstAvailable = result.devices.find(d => d.state === "device");
          setSelectedSerial(firstAvailable?.serial ?? result.devices[0].serial);
        }
      }
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally {
      setIsLoadingDevices(false);
    }
  }, [selectedSerial]);

  const handleCapture = useCallback(async (serialOverride?: string) => {
    const serial = serialOverride ?? selectedSerial;
    if (!serial) {
      return;
    }
    setIsCapturing(true);
    setError(null);
    try {
      const displayIdNum = displayId.trim() ? parseInt(displayId, 10) : null;
      if (displayId.trim() && isNaN(displayIdNum!)) {
        setError("Invalid display ID");
        setIsCapturing(false);
        return;
      }
      const result = await captureAdbScreenshot(serial, displayIdNum);
      if (result.success && result.imagePath) {
        setCapturedImagePath(result.imagePath);
      } else {
        setError(result.error ?? "Unknown error");
      }
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally {
      setIsCapturing(false);
    }
  }, [selectedSerial, displayId]);

  useEffect(() => {
    if (isOpen) {
      setCapturedImagePath(null);
      setError(null);
      setDisplayId("");
      hasAutoCaptured.current = false;
      loadDevices();
    }
  }, [isOpen, loadDevices]);

  useShortcut({
    id: `device-capture-use-image-${shortcutInstanceId}`,
    combo: "enter",
    scope: "modal",
    when: () => isOpen && !!capturedImagePath,
    onKeyDown: () => {
      void handleUseImage();
    },
  });

  useEffect(() => {
    if (
      !hasAutoCaptured.current &&
      devices.length > 0 &&
      selectedSerial &&
      !isLoadingDevices &&
      !isCapturing
    ) {
      const selectedDevice = devices.find(d => d.serial === selectedSerial);
      if (selectedDevice?.state === "device") {
        hasAutoCaptured.current = true;
        handleCapture(selectedSerial);
      }
    }
  }, [devices, selectedSerial, isLoadingDevices, isCapturing, handleCapture]);

  const handleUseImage = useCallback(async () => {
    if (!capturedImagePath) {
      return;
    }
    try {
      const file = await fetchImageAsFile(capturedImagePath, "device_capture.png");
      const shouldClose = await onImport([file]);
      if (shouldClose) {
        onClose();
      }
    } catch (e: any) {
      setError(e?.message ?? String(e));
    }
  }, [capturedImagePath, onImport, onClose]);

  const selectedDevice = devices.find((d) => d.serial === selectedSerial);

  return (
    <Dialog
      isOpen={isOpen}
      onClose={onClose}
      title={t("deviceCapture.title")}
      style={{ width: 600 }}
    >
      <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <label style={{ minWidth: 80 }}>{t("deviceCapture.selectDevice")}:</label>
          <HTMLSelect
            value={selectedSerial}
            onChange={(e) => setSelectedSerial(e.target.value)}
            disabled={isLoadingDevices || devices.length === 0}
            style={{ flex: 1 }}
          >
            {devices.length === 0 ? (
              <option value="">{t("deviceCapture.noDevices")}</option>
            ) : (
              devices.map((d) => (
                <option key={d.serial} value={d.serial}>
                  {d.name}
                </option>
              ))
            )}
          </HTMLSelect>
          <Button
            icon="refresh"
            onClick={loadDevices}
            disabled={isLoadingDevices}
            title={t("deviceCapture.refreshDevices")}
          />
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <label style={{ minWidth: 80 }}>{t("deviceCapture.displayId")}:</label>
          <InputGroup
            value={displayId}
            onChange={(e) => setDisplayId(e.target.value)}
            placeholder={t("deviceCapture.displayIdPlaceholder")}
            style={{ flex: 1 }}
          />
        </div>

        {error && (
          <div style={{ color: "#c23030", fontSize: 12, padding: "8px 12px", background: "#fff5f5", borderRadius: 4 }}>
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 8 }}>
          <Button
            intent="primary"
            onClick={() => handleCapture()}
            disabled={!selectedSerial || isCapturing || selectedDevice?.state !== "device"}
            loading={isCapturing}
            icon="camera"
          >
            {t("fileDialog.refreshScreenshot")}
          </Button>
        </div>

        <div style={{ flex: 1, minHeight: 300, border: "1px solid #d1d8e0", borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center", background: "#f5f8fa" }}>
          {isCapturing ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8 }}>
              <Spinner size={32} />
              <span>{t("deviceCapture.capturing")}</span>
            </div>
          ) : capturedImagePath ? (
            <img
              src={`/api/image?path=${encodeURIComponent(capturedImagePath)}`}
              alt="Captured"
              style={{ maxWidth: "100%", maxHeight: 300, objectFit: "contain" }}
            />
          ) : (
            <NonIdealState
              icon="camera"
              title={t("deviceCapture.preview")}
              description={t("deviceCapture.selectDevice")}
            />
          )}
        </div>
      </div>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, padding: "12px 16px", borderTop: "1px solid #d1d8e0" }}>
        <Button onClick={onClose}>{t("dialog.cancel")}</Button>
        <Button
          intent="primary"
          onClick={handleUseImage}
          disabled={!capturedImagePath}
        >
          {t("fileDialog.useThisImage")}
          {capturedImagePath && (
            <span style={{
              marginLeft: 8,
              padding: "2px 6px",
              background: "rgba(255,255,255,0.2)",
              borderRadius: 3,
              fontSize: 11,
              fontFamily: "monospace",
            }}>
              Enter
            </span>
          )}
        </Button>
      </div>
    </Dialog>
  );
};
