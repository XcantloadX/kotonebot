/** Conversion（Single → Multi）的 API 封装。 */

import { fetchJson, postJson, del } from "./client";

export interface ConversionMatch {
  /** Single 文档的 JSON 元数据文件路径（相对 pyproject_root），null 表示裸 PNG。 */
  singleMetaPath: string | null;
  /** Single 文档对应的图片文件路径（相对 pyproject_root）。 */
  singleImagePath: string;
  /** 匹配命中的目标图片路径（相对 pyproject_root）。 */
  matchedImagePath: string;
  /** 模板匹配得分。 */
  matchScore: number;
  /** 匹配区域左上角 X 坐标。 */
  matchX: number;
  /** 匹配区域左上角 Y 坐标。 */
  matchY: number;
  /** 匹配区域宽度。 */
  matchW: number;
  /** 匹配区域高度。 */
  matchH: number;
}

export interface ConfirmedMatch {
  /** Single 文档的 JSON 元数据文件路径（相对 pyproject_root），null 表示裸 PNG。 */
  singleMetaPath: string | null;
  /** Single 文档对应的图片文件路径（相对 pyproject_root）。 */
  singleImagePath: string;
  /** 匹配命中的目标图片路径（相对 pyproject_root）。 */
  matchedImagePath: string;
  /** 匹配区域左上角 X 坐标。 */
  matchX: number;
  /** 匹配区域左上角 Y 坐标。 */
  matchY: number;
  /** 匹配区域宽度。 */
  matchW: number;
  /** 匹配区域高度。 */
  matchH: number;
  /** 目标 Multi 文档的元数据文件路径（相对 pyproject_root），不指定时由后端推算。 */
  targetMetaPath?: string | null;
}

export interface ConversionScanData {
  /** 匹配结果列表。 */
  matches: ConversionMatch[];
}

export interface ConversionExecuteData {
  /** 被修改的 Multi 元数据文件路径列表。 */
  modifiedMetaPaths: string[];
  /** 被删除的 Single 元数据文件路径列表。 */
  deletedSingleMetaPaths: string[];
  /** 被删除的 Single 图片文件路径列表。 */
  deletedSingleImagePaths: string[];
}

export interface ScanStartData {
  /** 任务 ID。 */
  taskId: string;
}

export interface ScanProgress {
  /** 任务唯一标识。 */
  taskId: string;
  /** 当前状态。 */
  state: "pending" | "classifying" | "scanning" | "completed" | "cancelled" | "error";
  /** 待扫描总数。 */
  total: number;
  /** 已完成数量。 */
  current: number;
  /** 当前正在处理的文件名。 */
  currentFile: string;
  /** 匹配结果，仅在 completed 状态时存在。 */
  matches?: ConversionMatch[];
  /** 错误信息。 */
  error?: string | null;
}

export interface ScanRequest {
  mode: "all" | "files" | "device" | "current";
  imagePaths?: string[];
  screenshotPath?: string;
  /** 当前文档模式下要扫描的 single 图片路径。 */
  singleImagePath?: string;
}

/** 启动异步扫描任务。 */
export async function startScan(body: ScanRequest): Promise<ScanStartData> {
  return postJson<ScanStartData>("/api/conversion/scan", body);
}

/** 轮询扫描任务进度。 */
export async function fetchProgress(taskId: string): Promise<ScanProgress> {
  return fetchJson<ScanProgress>(`/api/conversion/scan_progress/${encodeURIComponent(taskId)}`);
}

/** 取消扫描任务。 */
export async function cancelScan(taskId: string): Promise<void> {
  return del(`/api/conversion/scan/${encodeURIComponent(taskId)}`);
}

export async function scanAll(): Promise<ConversionScanData> {
  return postJson<ConversionScanData>("/api/conversion/scan_all");
}

export async function scanFiles(imagePaths: string[]): Promise<ConversionScanData> {
  return postJson<ConversionScanData>("/api/conversion/scan_files", { imagePaths });
}

export async function scanDevice(screenshotPath: string): Promise<ConversionScanData> {
  return postJson<ConversionScanData>("/api/conversion/scan_device", { screenshotPath });
}

export async function executeConversion(matches: ConfirmedMatch[]): Promise<ConversionExecuteData> {
  return postJson<ConversionExecuteData>("/api/conversion/execute", { matches });
}
