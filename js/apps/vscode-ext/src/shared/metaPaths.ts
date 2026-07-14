import * as vscode from "vscode";

/** 判断 URI 是否为 meta 文档。 */
export function isMetaDocumentUri(uri: vscode.Uri): boolean {
  return uri.scheme === "file" && uri.fsPath.toLowerCase().endsWith(".png.json");
}

/** 判断路径是否为 meta 文件（*.png.json）。 */
export function isMetaPath(fsPath: string): boolean {
  return fsPath.toLowerCase().endsWith(".png.json");
}

/** 判断路径是否为图片文件（*.png）。 */
export function isImagePath(fsPath: string): boolean {
  return fsPath.toLowerCase().endsWith(".png");
}

/** 将 meta 文件路径映射为对应图片路径。 */
export function metaToImagePath(metaPath: string): string {
  if (!isMetaPath(metaPath)) {
    throw new Error(`Meta path must end with .png.json: ${metaPath}`);
  }
  return metaPath.slice(0, -".json".length);
}

/** 将图片路径映射为对应 meta 路径。 */
export function imageToMetaPath(imagePath: string): string {
  if (!isImagePath(imagePath)) {
    throw new Error(`Image path must end with .png: ${imagePath}`);
  }
  return `${imagePath}.json`;
}

/** 统一路径格式用于比较和去重。 */
export function normalizePathKey(fsPath: string): string {
  return fsPath.split("\\").join("/").toLowerCase();
}
