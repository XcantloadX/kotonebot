import { client, unwrap, postForm } from "./client";
import type { components } from "./schema";

/** 目录条目。 */
export type FileItem = components["schemas"]["ListDirItem"];
/** 项目根信息。 */
export type ProjectInfo = components["schemas"]["ProjectRootData"];
/** 文档重命名预检结果。 */
export type RenameDocumentPrecheckResult = components["schemas"]["RenameDocumentPrecheckResultModel"];
/** 文档重命名执行结果。 */
export type RenameDocumentExecuteResult = components["schemas"]["RenameDocumentExecuteResultModel"];
/** 创建文档结果。 */
export type CreateDocumentResult = components["schemas"]["CreateDocumentResult"];

export async function listDir(path: string): Promise<FileItem[]> {
  const res = await unwrap(client.GET("/api/fs/list_dir", { params: { query: { path } } }));
  return res.items;
}

export async function readText(path: string): Promise<string> {
  const res = await unwrap(client.GET("/api/fs/read_text", { params: { query: { path } } }));
  return res.content;
}

export async function writeText(path: string, content: string): Promise<void> {
  await unwrap(client.PUT("/api/fs/write_text", {
    params: { query: { path } },
    body: { content },
  }));
}

export async function renamePath(sourcePath: string, targetPath: string): Promise<void> {
  await unwrap(client.POST("/api/fs/rename", {
    body: { sourcePath, targetPath },
  }));
}

export async function precheckRenameDocument(sourceImagePath: string, targetImagePath: string): Promise<RenameDocumentPrecheckResult> {
  return unwrap(client.POST("/api/fs/rename_document/precheck", {
    body: { sourceImagePath, targetImagePath },
  }));
}

export async function executeRenameDocument(sourceImagePath: string, targetImagePath: string): Promise<RenameDocumentExecuteResult> {
  return unwrap(client.POST("/api/fs/rename_document/execute", {
    body: { sourceImagePath, targetImagePath },
  }));
}

export async function copyFile(sourcePath: string, targetPath: string): Promise<void> {
  await unwrap(client.POST("/api/fs/copy_file", {
    body: { sourcePath, targetPath },
  }));
}

export async function uploadFile(targetPath: string, file: File): Promise<void> {
  const formData = new FormData();
  formData.set("targetPath", targetPath);
  formData.set("file", file);
  await postForm("/api/fs/upload_file", formData);
}

export async function createDocument(targetPath: string, image: File): Promise<CreateDocumentResult> {
  const formData = new FormData();
  formData.set("targetPath", targetPath);
  formData.set("image", image);
  return postForm<CreateDocumentResult>("/api/document/create", formData);
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
  return unwrap(client.GET("/api/project/root"));
}

export async function listWorkspaceImages(): Promise<string[]> {
  const res = await unwrap(client.GET("/api/project/list_images"));
  return res.imagePaths;
}

export async function revealInExplorer(path: string): Promise<void> {
  await unwrap(client.POST("/api/fs/reveal_in_explorer", { params: { query: { path } } }));
}
