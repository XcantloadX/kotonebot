import { create } from "zustand";
import { getMetaIndex, updateMetaIndex } from "../api/metaIndex";
import { SymbolLite } from "../model/symbolIndex";

interface SymbolIndexState {
  indexVersion: number;
  contentHash: string;
  symbols: SymbolLite[];
  recentSymbolKeys: string[];
  initialized: boolean;
  initialize: () => Promise<void>;
  refetch: () => Promise<void>;
  patchMetaPath: (metaPath: string) => Promise<void>;
  markUsed: (symbolKey: string) => void;
}

const MAX_RECENT_SYMBOLS = 50;

export const useSymbolIndexStore = create<SymbolIndexState>((set, get) => ({
  indexVersion: 0,
  contentHash: "",
  symbols: [],
  recentSymbolKeys: [],
  initialized: false,

  initialize: async () => {
    if (get().initialized) {
      return;
    }
    const data = await getMetaIndex();
    set({
      indexVersion: data.indexVersion,
      contentHash: data.contentHash,
      symbols: data.symbols,
      initialized: true,
    });
  },

  refetch: async () => {
    const data = await getMetaIndex();
    set({
      indexVersion: data.indexVersion,
      contentHash: data.contentHash,
      symbols: data.symbols,
      initialized: true,
    });
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
  },

  markUsed: (symbolKey: string) =>
    set((state) => {
      const recent = [symbolKey, ...state.recentSymbolKeys.filter((it) => it !== symbolKey)].slice(0, MAX_RECENT_SYMBOLS);
      return { recentSymbolKeys: recent };
    }),
}));
