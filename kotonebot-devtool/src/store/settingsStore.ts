import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { persist } from 'zustand/middleware';

interface Settings {
  baseUrl: string;
  infoPanelWidth: number;
  theme: 'light' | 'dark';
}

interface SettingsState extends Settings {
  updateSettings: (settings: Partial<Settings>) => void;
  resetSettings: () => void;
}

const DEFAULT_SETTINGS: Settings = {
  baseUrl: 'http://localhost:8000',
  infoPanelWidth: 400,
  theme: 'light'
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    immer((set) => ({
      ...DEFAULT_SETTINGS,
      updateSettings: (settings: Partial<Settings>) =>
        set((state) => {
          Object.assign(state, settings);
        }),
      resetSettings: () =>
        set((state) => {
          Object.assign(state, DEFAULT_SETTINGS);
        })
    })),
    {
      name: 'debug-tool-settings'
    }
  )
); 