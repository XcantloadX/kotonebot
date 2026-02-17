import { fetchJson } from "./client";
import { MetaDiagnosticsSnapshot, SymbolSnapshotLite, SymbolUpdateResult } from "../model/symbolIndex";

export async function getMetaIndex(): Promise<SymbolSnapshotLite> {
  return fetchJson<SymbolSnapshotLite>("/api/meta/index");
}

export async function updateMetaIndex(metaPath: string): Promise<SymbolUpdateResult> {
  return fetchJson<SymbolUpdateResult>("/api/meta/index/update", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ metaPath }),
  });
}

export async function getMetaDiagnostics(): Promise<MetaDiagnosticsSnapshot> {
  return fetchJson<MetaDiagnosticsSnapshot>("/api/meta/diagnostics");
}

export interface CloneVariantToImagePayload {
  sourceMetaPath: string;
  targetImagePath: string;
  variant: string;
  forceOverwrite: boolean;
}

export async function cloneVariantToImage(payload: CloneVariantToImagePayload): Promise<{ targetMetaPath: string; definitionCount: number }> {
  return fetchJson<{ targetMetaPath: string; definitionCount: number }>("/api/meta/variant/clone_to_image", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export interface PreCheckVariantImportPathPayload {
  sourceMetaPath: string;
  baseImagePath: string;
  variant: string;
  image: File;
}

export interface PreCheckVariantImportPathResult {
  targetImagePath: string;
  targetImageExists: boolean;
  targetMetaPath: string;
  targetMetaExists: boolean;
  copiedDefinitions: { definitionId: string; name: string }[];
  skippedDefinitions: { definitionId: string; name: string; reason: string }[];
}

export async function preCheckVariantImportPath(payload: PreCheckVariantImportPathPayload): Promise<PreCheckVariantImportPathResult> {
  const formData = new FormData();
  formData.set("sourceMetaPath", payload.sourceMetaPath);
  formData.set("baseImagePath", payload.baseImagePath);
  formData.set("variant", payload.variant);
  formData.set("image", payload.image);
  return fetchJson<PreCheckVariantImportPathResult>("/api/meta/variant/import/precheck_path", {
    method: "POST",
    body: formData,
  });
}

export interface ImportVariantImagePayload {
  baseImagePath: string;
  variant: string;
  image: File;
  deleteExistingTarget?: boolean;
}

export async function importVariantImage(payload: ImportVariantImagePayload): Promise<{ targetImagePath: string; size: number }> {
  const formData = new FormData();
  formData.set("baseImagePath", payload.baseImagePath);
  formData.set("variant", payload.variant);
  formData.set("image", payload.image);
  formData.set("deleteExistingTarget", payload.deleteExistingTarget ? "true" : "false");
  return fetchJson<{ targetImagePath: string; size: number }>("/api/meta/variant/import_image", {
    method: "POST",
    body: formData,
  });
}
