/** Conversion（Single → Multi）的 API 封装。 */

import { client, unwrap } from "./client";
import type { components } from "./schema";

/** 单个匹配结果：single 文档模板在目标图片中的命中记录。 */
export type ConversionMatch = components["schemas"]["ConversionMatch"];
/** 用户确认后的单条转换项。 */
export type ConfirmedMatch = components["schemas"]["ConfirmedMatch"];
/** 扫描任务进度。 */
export type ScanProgress = components["schemas"]["ScanProgress"];
/** 启动扫描请求。 */
export type ScanRequest = components["schemas"]["ScanRequest"];
/** 启动扫描响应。 */
export type ScanStartData = components["schemas"]["ScanStartResponse"];
/** 转换执行结果。 */
export type ConversionExecuteData = components["schemas"]["ConversionExecuteResponse"];

/** 启动异步扫描任务。 */
export async function startScan(body: ScanRequest): Promise<ScanStartData> {
  return unwrap(client.POST("/api/conversion/scan", { body }));
}

/** 轮询扫描任务进度。 */
export async function fetchProgress(taskId: string): Promise<ScanProgress> {
  return unwrap(client.GET("/api/conversion/scan_progress/{task_id}", {
    params: { path: { task_id: taskId } },
  }));
}

/** 取消扫描任务。 */
export async function cancelScan(taskId: string): Promise<void> {
  await unwrap(client.DELETE("/api/conversion/scan/{task_id}", {
    params: { path: { task_id: taskId } },
  }));
}

export async function executeConversion(matches: ConfirmedMatch[]): Promise<ConversionExecuteData> {
  return unwrap(client.POST("/api/conversion/execute", { body: { matches } }));
}
