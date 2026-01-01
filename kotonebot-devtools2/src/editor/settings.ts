import { create } from "zustand";
import { persist } from "zustand/middleware";

export type FileDialogViewMode = "list" | "thumb";

interface SettingsState {
  fileDialogViewMode: FileDialogViewMode;
  fileDialogThumbSize: number;
  setFileDialogViewMode: (mode: FileDialogViewMode) => void;
  setFileDialogThumbSize: (size: number) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      fileDialogViewMode: "list",
      fileDialogThumbSize: 120,
      setFileDialogViewMode: (mode) => set({ fileDialogViewMode: mode }),
      setFileDialogThumbSize: (size) => set({ fileDialogThumbSize: size }),
    }),
    {
      name: "kotonebot-devtools2-settings",
    },
  ),
);
