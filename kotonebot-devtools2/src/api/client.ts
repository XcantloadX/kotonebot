export interface ResponseModel<T> {
  success: boolean;
  message?: string;
  data?: T;
}

export async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API Error ${res.status}: ${text}`);
  }
  const json = await res.json() as ResponseModel<T>;
  if (!json.success) {
    throw new Error(json.message || "Unknown API Error");
  }
  return json.data as T;
}
