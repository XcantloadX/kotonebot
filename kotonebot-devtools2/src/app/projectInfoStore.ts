import { create } from "zustand";
import { getProjectInfo, ProjectInfo } from "../api/fs";

type ProjectInfoStatus = "idle" | "loading" | "ready" | "error";

interface ProjectInfoState {
  status: ProjectInfoStatus;
  data: ProjectInfo | null;
  error: string | null;
  ensureLoaded: () => Promise<void>;
  refresh: () => Promise<void>;
}

let loadingPromise: Promise<void> | null = null;

async function fetchAndStore(set: (updater: Partial<ProjectInfoState>) => void): Promise<void> {
  if (loadingPromise) {
    await loadingPromise;
    return;
  }
  loadingPromise = (async () => {
    set({ status: "loading", error: null });
    try {
      const data = await getProjectInfo();
      set({ status: "ready", data, error: null });
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      set({ status: "error", error: message });
    }
  })();

  await loadingPromise;
  loadingPromise = null;
}

export const useProjectInfoStore = create<ProjectInfoState>((set, get) => ({
  status: "idle",
  data: null,
  error: null,

  ensureLoaded: async () => {
    if (get().status === "ready") {
      return;
    }
    await fetchAndStore((updater) => set((state) => ({ ...state, ...updater })));
  },

  refresh: async () => {
    await fetchAndStore((updater) => set((state) => ({ ...state, ...updater })));
  },
}));
