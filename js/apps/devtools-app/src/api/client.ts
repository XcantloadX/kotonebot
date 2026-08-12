import createClient from "openapi-fetch";
import type { paths } from "./schema";

/** openapi-fetch 类型化客户端实例，请求同源相对路径（SPA 由后端提供，开发环境由 Vite 代理）。 */
export const client = createClient<paths>();

/** 响应信封模型，对应后端 ``ResponseModel`` 的 JSON 结构。 */
export interface ResponseModel<T> {
  success: boolean;
  message?: string | null;
  data?: T | null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** 从错误对象中提取用户可读消息（后端错误信封或 FastAPI HTTP 错误）。 */
function extractErrorMessage(error: unknown, status: number): string {
  if (isRecord(error)) {
    if (typeof error.message === "string" && error.message) return error.message;
    if (typeof error.detail === "string" && error.detail) return error.detail;
  }
  return `HTTP ${status}`;
}

/** 解包响应信封并返回 data，请求失败或信封标记失败时抛出错误。 */
export async function unwrap<T>(req: Promise<{
  data?: ResponseModel<T> | null;
  error?: unknown;
  response: Response;
}>): Promise<T> {
  const { data, error, response } = await req;
  if (!response.ok || !data?.success) {
    throw new Error(extractErrorMessage(data?.message ?? error, response.status));
  }
  return data.data as T;
}

/** 发送 multipart/form-data 请求并解包信封。
 *
 * openapi-fetch 对二进制字段的 multipart body 类型支持不佳，文件上传类端点单独走原生 fetch。
 */
export async function postForm<T>(url: string, formData: FormData): Promise<T> {
  const res = await fetch(url, { method: "POST", body: formData });
  const body = await res.json() as ResponseModel<T>;
  if (!res.ok || !body.success) {
    throw new Error(body.message || `HTTP ${res.status}`);
  }
  return body.data as T;
}
