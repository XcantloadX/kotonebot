import { fetchJson } from "./client";

export interface AdbDevice {
  serial: string;
  state: string;
  name: string;
}

export interface ListAdbDevicesResult {
  devices: AdbDevice[];
  error?: string;
}

export interface CaptureScreenshotResult {
  success: boolean;
  imagePath?: string;
  imageUrl?: string;
  error?: string;
}

export async function listAdbDevices(): Promise<ListAdbDevicesResult> {
  return fetchJson<ListAdbDevicesResult>("/api/device/adb/list");
}

export async function captureAdbScreenshot(
  serial: string,
  displayId?: number | null
): Promise<CaptureScreenshotResult> {
  const params = new URLSearchParams({ serial });
  if (displayId != null) {
    params.append("displayId", String(displayId));
  }
  return fetchJson<CaptureScreenshotResult>(`/api/device/adb/screenshot?${params.toString()}`);
}
