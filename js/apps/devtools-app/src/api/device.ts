import { client, unwrap } from "./client";
import type { components } from "./schema";

/** ADB 设备信息。 */
export type AdbDevice = components["schemas"]["DeviceInfo"];
/** ADB 设备列表结果。 */
export type ListAdbDevicesResult = components["schemas"]["DeviceListResult"];
/** 设备截图结果。 */
export type CaptureScreenshotResult = components["schemas"]["CaptureScreenshotResponse"];

export async function listAdbDevices(): Promise<ListAdbDevicesResult> {
  return unwrap(client.GET("/api/device/adb/list"));
}

export async function captureAdbScreenshot(
  serial: string,
  displayId?: number | null
): Promise<CaptureScreenshotResult> {
  const query: { serial: string; displayId?: number } = { serial };
  if (displayId != null) {
    query.displayId = displayId;
  }
  return unwrap(client.GET("/api/device/adb/screenshot", { params: { query } }));
}
