export interface ResponseModel<T> {
  success: boolean;
  message?: string;
  data?: T;
}

export async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  const body = await res.json() as ResponseModel<T>;
  if (!res.ok || !body.success) {
    throw new Error(body.message || `HTTP ${res.status}`);
  }
  return body.data as T;
}

export async function postJson<T>(url: string, body?: unknown): Promise<T> {
  return fetchJson<T>(url, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
}

/** 发送 DELETE 请求，忽略响应体。 */
export async function del(url: string): Promise<void> {
  const res = await fetch(url, { method: "DELETE" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.message || `HTTP ${res.status}`);
  }
}
