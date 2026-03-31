import { create } from "zustand";
import { getMetaDiagnostics, getMetaIndex, getProjectSymbolTree, updateMetaIndex } from "../api/metaIndex";
import { DiagnosticItem, ProjectSymbolTreeNode, SymbolLite } from "../model/symbolIndex";

interface DiagnosticStats {
  total: number;
  error: number;
  warning: number;
  info: number;
}

interface SymbolIndexState {
  indexVersion: number;
  contentHash: string;
  symbols: SymbolLite[];
  projectSymbolTree: ProjectSymbolTreeNode[];
  diagnosticsByFile: Record<string, DiagnosticItem[]>;
  diagnosticStats: DiagnosticStats;
  recentSymbolKeys: string[];
  initialized: boolean;
  initialize: () => Promise<void>;
  refetch: () => Promise<void>;
  refetchDiagnostics: () => Promise<void>;
  refetchProjectSymbolTree: () => Promise<void>;
  patchMetaPath: (metaPath: string) => Promise<void>;
  markUsed: (symbolKey: string) => void;
}

const MAX_RECENT_SYMBOLS = 50;

export const useSymbolIndexStore = create<SymbolIndexState>((set, get) => ({
  indexVersion: 0,
  contentHash: "",
  symbols: [],
  projectSymbolTree: [],
  diagnosticsByFile: {},
  diagnosticStats: { total: 0, error: 0, warning: 0, info: 0 },
  recentSymbolKeys: [],
  initialized: false,

  initialize: async () => {
    if (get().initialized) {
      return;
    }
    const [indexData, diagnosticsData, projectSymbolTree] = await Promise.all([
      getMetaIndex(),
      getMetaDiagnostics(),
      getProjectSymbolTree(),
    ]);
    set({
      indexVersion: indexData.indexVersion,
      contentHash: indexData.contentHash,
      symbols: indexData.symbols,
      projectSymbolTree,
      diagnosticsByFile: diagnosticsData.diagnosticsByFile,
      diagnosticStats: diagnosticsData.stats,
      initialized: true,
    });
  },

  refetch: async () => {
    const [indexData, diagnosticsData, projectSymbolTree] = await Promise.all([
      getMetaIndex(),
      getMetaDiagnostics(),
      getProjectSymbolTree(),
    ]);
    set({
      indexVersion: indexData.indexVersion,
      contentHash: indexData.contentHash,
      symbols: indexData.symbols,
      projectSymbolTree,
      diagnosticsByFile: diagnosticsData.diagnosticsByFile,
      diagnosticStats: diagnosticsData.stats,
      initialized: true,
    });
  },

  refetchDiagnostics: async () => {
    const diagnosticsData = await getMetaDiagnostics();
    set({
      diagnosticsByFile: diagnosticsData.diagnosticsByFile,
      diagnosticStats: diagnosticsData.stats,
    });
  },

  refetchProjectSymbolTree: async () => {
    const projectSymbolTree = await getProjectSymbolTree();
    set({ projectSymbolTree });
  },

  patchMetaPath: async (metaPath: string) => {
    const current = get();
    const update = await updateMetaIndex(metaPath);
    const shouldRefetch =
      update.indexVersion <= current.indexVersion ||
      (current.contentHash !== "" && update.contentHash === current.contentHash);

    if (shouldRefetch) {
      await get().refetch();
      return;
    }

    const removedKeys = new Set(update.removedSymbolKeys);
    const upsertedByKey = new Map(update.upsertedSymbols.map((symbol) => [symbol.symbolKey, symbol]));
    const kept = current.symbols.filter((symbol) => !removedKeys.has(symbol.symbolKey) && !upsertedByKey.has(symbol.symbolKey));

    set({
      indexVersion: update.indexVersion,
      contentHash: update.contentHash,
      symbols: [...kept, ...update.upsertedSymbols],
      initialized: true,
    });
    await Promise.all([get().refetchDiagnostics(), get().refetchProjectSymbolTree()]);
  },

  markUsed: (symbolKey: string) =>
    set((state) => {
      const recent = [symbolKey, ...state.recentSymbolKeys.filter((it) => it !== symbolKey)].slice(0, MAX_RECENT_SYMBOLS);
      return { recentSymbolKeys: recent };
    }),
}));
