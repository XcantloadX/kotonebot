import { client, unwrap, postForm } from "./client";
import type { components } from "./schema";
import { MetaDiagnosticsSnapshot, ProjectSymbolTreeNode, SymbolSnapshotLite, SymbolUpdateResult } from "../model/symbolIndex";

/** 变体克隆请求。 */
export type CloneVariantToImagePayload = components["schemas"]["CloneVariantToImageRequest"];
/** 变体克隆结果。 */
export type VariantCloneResult = components["schemas"]["VariantCloneResult"];
/** 变体导入预检结果。 */
export type PreCheckVariantImportPathResult = components["schemas"]["VariantImportPrecheckResult"];
/** 变体导入结果。 */
export type VariantImportImageResult = components["schemas"]["VariantImportResult"];
/** 复制选中 prefab 到变体的预检请求。 */
export type PreCheckCopySelectedPrefabToVariantPayload = components["schemas"]["PrecheckCopySelectedPrefabToVariantRequest"];
/** 复制选中 prefab 到变体的预检结果。 */
export type PreCheckCopySelectedPrefabToVariantResult = components["schemas"]["CopyPrefabPrecheckResult"];
/** 复制选中 prefab 到变体的请求。 */
export type CopySelectedPrefabToVariantPayload = components["schemas"]["CopySelectedPrefabToVariantRequest"];
/** 复制选中 prefab 到变体的结果。 */
export type CopySelectedPrefabToVariantResult = components["schemas"]["CopyPrefabResult"];

export async function getMetaIndex(): Promise<SymbolSnapshotLite> {
  const result = await unwrap(client.GET("/api/meta/index"));
  // 线格式的 primaryGeometry 为宽泛 dict，收窄为 UI 使用的富几何类型
  return result as unknown as SymbolSnapshotLite;
}

export async function updateMetaIndex(metaPath: string): Promise<SymbolUpdateResult> {
  const result = await unwrap(client.POST("/api/meta/index/update", { body: { metaPath } }));
  return result as unknown as SymbolUpdateResult;
}

export async function getMetaDiagnostics(): Promise<MetaDiagnosticsSnapshot> {
  const result = await unwrap(client.GET("/api/meta/diagnostics"));
  // 线格式诊断含行列号等额外字段且 severity 为 string，收窄为 UI 视图类型
  return result as unknown as MetaDiagnosticsSnapshot;
}

export async function getProjectSymbolTree(): Promise<ProjectSymbolTreeNode[]> {
  const result = await unwrap(client.GET("/api/project/symbol_tree"));
  // 线格式叶子节点含 kind/label 等字段，与 UI 视图类型存在差异
  return result as unknown as ProjectSymbolTreeNode[];
}

export async function cloneVariantToImage(payload: CloneVariantToImagePayload): Promise<VariantCloneResult> {
  return unwrap(client.POST("/api/meta/variant/clone_to_image", { body: payload }));
}

export interface PreCheckVariantImportPathPayload {
  sourceMetaPath: string;
  baseImagePath: string;
  variant: string;
  image: File;
}

export async function preCheckVariantImportPath(payload: PreCheckVariantImportPathPayload): Promise<PreCheckVariantImportPathResult> {
  const formData = new FormData();
  formData.set("sourceMetaPath", payload.sourceMetaPath);
  formData.set("baseImagePath", payload.baseImagePath);
  formData.set("variant", payload.variant);
  formData.set("image", payload.image);
  return postForm<PreCheckVariantImportPathResult>("/api/meta/variant/import/precheck_path", formData);
}

export interface ImportVariantImagePayload {
  baseImagePath: string;
  variant: string;
  image: File;
  deleteExistingTarget?: boolean;
}

export async function importVariantImage(payload: ImportVariantImagePayload): Promise<VariantImportImageResult> {
  const formData = new FormData();
  formData.set("baseImagePath", payload.baseImagePath);
  formData.set("variant", payload.variant);
  formData.set("image", payload.image);
  formData.set("deleteExistingTarget", payload.deleteExistingTarget ? "true" : "false");
  return postForm<VariantImportImageResult>("/api/meta/variant/import_image", formData);
}

export async function preCheckCopySelectedPrefabToVariant(
  payload: PreCheckCopySelectedPrefabToVariantPayload
): Promise<PreCheckCopySelectedPrefabToVariantResult> {
  return unwrap(client.POST("/api/meta/variant/copy_selected_prefab/precheck", { body: payload }));
}

export async function copySelectedPrefabToVariant(payload: CopySelectedPrefabToVariantPayload): Promise<CopySelectedPrefabToVariantResult> {
  return unwrap(client.POST("/api/meta/variant/copy_selected_prefab", { body: payload }));
}
