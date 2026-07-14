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
