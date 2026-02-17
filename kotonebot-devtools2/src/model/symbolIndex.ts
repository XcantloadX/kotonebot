import { ResourceType } from "./metaV2";

export type PrimaryGeometry =
  | { kind: "rect"; x1: number; y1: number; x2: number; y2: number }
  | { kind: "image"; x1: number; y1: number; x2: number; y2: number }
  | { kind: "point"; x: number; y: number };

export interface SymbolLite {
  symbolKey: string;
  definitionId: string;
  type: ResourceType | string;
  name: string;
  displayName: string | null;
  prefabId: string | null;
  variant: string | null;
  metaPath: string;
  imagePath: string;
  primaryGeometry?: PrimaryGeometry | null;
  searchText: string;
}

export interface SymbolSnapshotLite {
  indexVersion: number;
  contentHash: string;
  symbols: SymbolLite[];
  stats: {
    fileCount: number;
    symbolCount: number;
    diagnosticCount: number;
  };
}

export interface DiagnosticItem {
  code: string;
  severity: "error" | "warning" | "info";
  message: string;
  meta_path: string;
  definition_id: string | null;
  field_path: string | null;
}

export interface MetaDiagnosticsSnapshot {
  indexVersion: number;
  diagnosticsByFile: Record<string, DiagnosticItem[]>;
  stats: {
    total: number;
    error: number;
    warning: number;
    info: number;
  };
}

export interface SymbolUpdateResult {
  indexVersion: number;
  contentHash: string;
  updatedMetaPath: string;
  removedSymbolKeys: string[];
  upsertedSymbols: SymbolLite[];
  diagnostics: DiagnosticItem[];
}
