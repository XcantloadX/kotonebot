import { create } from "zustand";
import { persist } from "zustand/middleware";
import { getProjectInfo } from "../api/fs";

const STORAGE_KEY = "kotonebot-devtools2-recent-open-v1";
const MAX_RECENT_ITEMS = 50;
const DEFAULT_WORKSPACE_KEY = "default";

export type RecentOpenSource = "file-dialog" | "symbol" | "host" | "other";

export interface RecentOpenItem {
  imagePath: string;
  metaPath: string;
  openedAt: number;
  source: RecentOpenSource;
}

interface RecentOpenState {
  initialized: boolean;
  currentWorkspaceKey: string;
  itemsByWorkspace: Record<string, RecentOpenItem[]>;
  ensureWorkspace: () => Promise<void>;
  setWorkspaceRoot: (resourceRoot: string | null | undefined) => void;
  addRecent: (item: Omit<RecentOpenItem, "openedAt"> & { openedAt?: number }) => void;
  removeRecentByMetaPath: (metaPath: string) => void;
  clearCurrentWorkspace: () => void;
}

let workspaceInitPromise: Promise<void> | null = null;

function normalizePath(path: string): string {
  return path.replace(/\\/g, "/").trim().toLowerCase();
}

function toWorkspaceKey(resourceRoot: string): string {
  const normalized = normalizePath(resourceRoot);
  if (normalized.length === 0) {
    return DEFAULT_WORKSPACE_KEY;
  }
  // djb2 hash to avoid exposing full local path in storage key.
  let hash = 5381;
  for (let i = 0; i < normalized.length; i += 1) {
    hash = ((hash << 5) + hash) + normalized.charCodeAt(i);
    hash |= 0;
  }
  return `ws_${(hash >>> 0).toString(36)}`;
}

export const useRecentOpenStore = create<RecentOpenState>()(
  persist(
    (set, get) => ({
      initialized: false,
      currentWorkspaceKey: DEFAULT_WORKSPACE_KEY,
      itemsByWorkspace: {},

      ensureWorkspace: async () => {
        const current = get();
        if (current.initialized) {
          return;
        }
        if (workspaceInitPromise) {
          await workspaceInitPromise;
          return;
        }
        workspaceInitPromise = (async () => {
          try {
            const info = await getProjectInfo();
            get().setWorkspaceRoot(info?.resource_root);
          } catch {
            get().setWorkspaceRoot(null);
          }
        })();
        await workspaceInitPromise;
        workspaceInitPromise = null;
      },

      setWorkspaceRoot: (resourceRoot) => set(() => {
        const nextKey = toWorkspaceKey(resourceRoot ?? "");
        return {
          initialized: true,
          currentWorkspaceKey: nextKey,
        };
      }),

      addRecent: (item) => set((state) => {
        const workspaceKey = state.currentWorkspaceKey || DEFAULT_WORKSPACE_KEY;
        const normalizedMetaPath = normalizePath(item.metaPath);
        if (normalizedMetaPath.length === 0) {
          return {};
        }

        const currentItems = state.itemsByWorkspace[workspaceKey] ?? [];
        const next: RecentOpenItem = {
          imagePath: item.imagePath,
          metaPath: item.metaPath,
          source: item.source,
          openedAt: item.openedAt ?? Date.now(),
        };

        const deduped = currentItems.filter((it) => normalizePath(it.metaPath) !== normalizedMetaPath);
        const nextItems = [next, ...deduped].slice(0, MAX_RECENT_ITEMS);

        return {
          itemsByWorkspace: {
            ...state.itemsByWorkspace,
            [workspaceKey]: nextItems,
          },
        };
      }),

      removeRecentByMetaPath: (metaPath) => set((state) => {
        const workspaceKey = state.currentWorkspaceKey || DEFAULT_WORKSPACE_KEY;
        const currentItems = state.itemsByWorkspace[workspaceKey] ?? [];
        const target = normalizePath(metaPath);
        return {
          itemsByWorkspace: {
            ...state.itemsByWorkspace,
            [workspaceKey]: currentItems.filter((it) => normalizePath(it.metaPath) !== target),
          },
        };
      }),

      clearCurrentWorkspace: () => set((state) => {
        const workspaceKey = state.currentWorkspaceKey || DEFAULT_WORKSPACE_KEY;
        return {
          itemsByWorkspace: {
            ...state.itemsByWorkspace,
            [workspaceKey]: [],
          },
        };
      }),
    }),
    {
      name: STORAGE_KEY,
      version: 1,
      migrate: (persistedState) => {
        const state = persistedState as Partial<RecentOpenState> | undefined;
        if (!state || typeof state !== "object") {
          return {
            initialized: false,
            currentWorkspaceKey: DEFAULT_WORKSPACE_KEY,
            itemsByWorkspace: {},
          } as RecentOpenState;
        }
        return {
          initialized: false,
          currentWorkspaceKey: typeof state.currentWorkspaceKey === "string" ? state.currentWorkspaceKey : DEFAULT_WORKSPACE_KEY,
          itemsByWorkspace: typeof state.itemsByWorkspace === "object" && state.itemsByWorkspace !== null
            ? state.itemsByWorkspace
            : {},
        } as RecentOpenState;
      },
      partialize: (state) => ({
        currentWorkspaceKey: state.currentWorkspaceKey,
        itemsByWorkspace: state.itemsByWorkspace,
      }),
    },
  ),
);
