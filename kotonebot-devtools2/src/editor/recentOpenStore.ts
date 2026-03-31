import { create } from "zustand";
import { persist } from "zustand/middleware";
import { toWorkspaceKey } from "../app/workspace";

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
  currentWorkspaceKey: string;
  itemsByWorkspace: Record<string, RecentOpenItem[]>;
  setWorkspaceRoot: (resourceRoot: string | null | undefined) => void;
  addRecent: (item: Omit<RecentOpenItem, "openedAt"> & { openedAt?: number }) => void;
  removeRecentByMetaPath: (metaPath: string) => void;
  clearCurrentWorkspace: () => void;
}

function normalizePath(path: string): string {
  return path.replace(/\\/g, "/").trim().toLowerCase();
}

export const useRecentOpenStore = create<RecentOpenState>()(
  persist(
    (set) => ({
      currentWorkspaceKey: DEFAULT_WORKSPACE_KEY,
      itemsByWorkspace: {},

      setWorkspaceRoot: (resourceRoot) => set((state) => {
        const nextKey = toWorkspaceKey(resourceRoot);
        const shouldMigrateDefault =
          state.currentWorkspaceKey === DEFAULT_WORKSPACE_KEY
          && nextKey !== DEFAULT_WORKSPACE_KEY
          && (state.itemsByWorkspace[nextKey] ?? []).length === 0
          && (state.itemsByWorkspace[DEFAULT_WORKSPACE_KEY] ?? []).length > 0;

        const nextItemsByWorkspace = shouldMigrateDefault
          ? {
              ...state.itemsByWorkspace,
              [nextKey]: state.itemsByWorkspace[DEFAULT_WORKSPACE_KEY],
              [DEFAULT_WORKSPACE_KEY]: [],
            }
          : state.itemsByWorkspace;

        return {
          currentWorkspaceKey: nextKey,
          itemsByWorkspace: nextItemsByWorkspace,
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
            currentWorkspaceKey: DEFAULT_WORKSPACE_KEY,
            itemsByWorkspace: {},
          } as RecentOpenState;
        }
        return {
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
