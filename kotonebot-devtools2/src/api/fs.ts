import { fetchJson } from "./client";

export interface FileItem {
  name: string;
  isDirectory: boolean;
  path: string;
  isImage?: boolean;
  thumbnailUrl?: string;
}

export async function listDir(path: string): Promise<FileItem[]> {
  const res = await fetchJson<{ items: FileItem[] }>(`/api/fs/list_dir?path=${encodeURIComponent(path)}`);
  return res.items;
}

export async function readText(path: string): Promise<string> {
  const res = await fetchJson<{ content: string }>(`/api/fs/read_text?path=${encodeURIComponent(path)}`);
  return res.content;
}

export async function writeText(path: string, content: string): Promise<void> {
  await fetchJson(`/api/fs/write_text?path=${encodeURIComponent(path)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
}

export function getImageUrl(path: string): string {
  return `/api/image?path=${encodeURIComponent(path)}`;
}

export async function getProjectInfo(): Promise<{ resource_root: string; resource_variants?: string[]; editor?: { resource_path?: string; prefabs_module?: string } }> {
  return fetchJson(`/api/project/root`);
}
