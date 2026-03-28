import { create } from "zustand";
import { persist } from "zustand/middleware";

export type FileDialogViewMode = "list" | "thumb" | "tree";
export type ProblemsSeverityFilter = "all" | "error" | "warning" | "info";

interface SettingsState {
  fileDialogViewMode: FileDialogViewMode;
  fileDialogThumbSize: number;
  problemsVisible: boolean;
  problemsHeight: number;
  problemsSeverityFilter: ProblemsSeverityFilter;
  problemsQuery: string;
  rightPanelWidth: number;
  setFileDialogViewMode: (mode: FileDialogViewMode) => void;
  setFileDialogThumbSize: (size: number) => void;
  setProblemsVisible: (visible: boolean) => void;
  setProblemsHeight: (height: number) => void;
  setProblemsSeverityFilter: (filter: ProblemsSeverityFilter) => void;
  setProblemsQuery: (query: string) => void;
  setRightPanelWidth: (width: number) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      fileDialogViewMode: "list",
      fileDialogThumbSize: 120,
      problemsVisible: false,
      problemsHeight: 220,
      problemsSeverityFilter: "all",
      problemsQuery: "",
      rightPanelWidth: 300,
      setFileDialogViewMode: (mode) => set({ fileDialogViewMode: mode }),
      setFileDialogThumbSize: (size) => set({ fileDialogThumbSize: size }),
      setProblemsVisible: (visible) => set({ problemsVisible: visible }),
      setProblemsHeight: (height) => set({ problemsHeight: height }),
      setProblemsSeverityFilter: (filter) => set({ problemsSeverityFilter: filter }),
      setProblemsQuery: (query) => set({ problemsQuery: query }),
      setRightPanelWidth: (width) => set({ rightPanelWidth: width }),
    }),
    {
      name: "kotonebot-devtools2-settings",
    },
  ),
);
