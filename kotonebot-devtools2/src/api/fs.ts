import { fetchJson } from "./client";

export interface FileItem {
  name: string;
  isDirectory: boolean;
  path: string;
  isImage?: boolean;
  thumbnailUrl?: string;
}

export interface ProjectInfo {
  resource_root: string;
  variant?: {
    variants?: string[];
    base?: string;
    path_pattern?: string;
  };
  editor?: {
    resource_path?: string;
    prefabs_module?: string;
  };
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

export async function renamePath(sourcePath: string, targetPath: string): Promise<void> {
  await fetchJson("/api/fs/rename", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sourcePath, targetPath }),
  });
}

export interface RenameDocumentPrecheckResult {
  documents: Array<{
    variant: string;
    sourceImagePath: string;
    targetImagePath: string;
    sourceMetaPath: string;
    targetMetaPath: string;
  }>;
  fileRenames: Array<{
    kind: "image" | "meta";
    variant: string;
    sourcePath: string;
    targetPath: string;
  }>;
  conflicts: string[];
  hasConflicts: boolean;
}

export interface RenameDocumentExecuteResult {
  documents: Array<{
    variant: string;
    sourceImagePath: string;
    targetImagePath: string;
    sourceMetaPath: string;
    targetMetaPath: string;
  }>;
  fileRenames: Array<{
    kind: "image" | "meta";
    variant: string;
    sourcePath: string;
    targetPath: string;
  }>;
  renamedFileCount: number;
  renamedDocumentCount: number;
}

export async function precheckRenameDocument(sourceImagePath: string, targetImagePath: string): Promise<RenameDocumentPrecheckResult> {
  return fetchJson<RenameDocumentPrecheckResult>("/api/fs/rename_document/precheck", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sourceImagePath, targetImagePath }),
  });
}

export async function executeRenameDocument(sourceImagePath: string, targetImagePath: string): Promise<RenameDocumentExecuteResult> {
  return fetchJson<RenameDocumentExecuteResult>("/api/fs/rename_document/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sourceImagePath, targetImagePath }),
  });
}

export async function copyFile(sourcePath: string, targetPath: string): Promise<void> {
  await fetchJson("/api/fs/copy_file", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sourcePath, targetPath }),
  });
}

export async function uploadFile(targetPath: string, file: File): Promise<void> {
  const formData = new FormData();
  formData.set("targetPath", targetPath);
  formData.set("file", file);
  await fetchJson("/api/fs/upload_file", {
    method: "POST",
    body: formData,
  });
}

export function getImageUrl(path: string): string {
  return `/api/image?path=${encodeURIComponent(path)}`;
}

export async function fetchImageAsFile(path: string, filename: string): Promise<File> {
  const response = await fetch(getImageUrl(path));
  if (!response.ok) {
    throw new Error(`Failed to fetch image: ${response.status}`);
  }
  const blob = await response.blob();
  return new File([blob], filename, { type: blob.type || "image/png" });
}

export async function getProjectInfo(): Promise<ProjectInfo> {
  return fetchJson(`/api/project/root`);
}

export async function revealInExplorer(path: string): Promise<void> {
  await fetchJson(`/api/fs/reveal_in_explorer?path=${encodeURIComponent(path)}`, { method: "POST" });
}
