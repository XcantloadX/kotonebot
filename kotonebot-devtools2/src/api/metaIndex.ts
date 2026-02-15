import { fetchJson } from "./client";
import { SymbolSnapshotLite, SymbolUpdateResult } from "../model/symbolIndex";

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
