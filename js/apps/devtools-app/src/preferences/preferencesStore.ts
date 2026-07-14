import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import i18n, { resolveSystemLanguage, LanguageOption } from '../i18n';

export interface AiConfig {
  providerType: "openai" | "anthropic" | "gemini";
  endpoint: string;
  model: string;
  apiKey: string;
}

interface PreferencesState {
  language: LanguageOption;
  ai: AiConfig;
  setLanguage: (lang: LanguageOption) => void;
  setAiConfig: (patch: Partial<AiConfig>) => void;
}

function applyLanguage(lang: LanguageOption) {
  if (lang === 'system') {
    i18n.changeLanguage(resolveSystemLanguage());
  } else {
    i18n.changeLanguage(lang);
  }
}

export const usePreferencesStore = create<PreferencesState>()(
  persist(
    (set) => ({
      language: 'system',
      ai: {
        providerType: "openai",
        endpoint: "",
        model: "",
        apiKey: "",
      },
      setLanguage: (lang) => {
        applyLanguage(lang);
        set({ language: lang });
      },
      setAiConfig: (patch) => {
        set((state) => ({ ai: { ...state.ai, ...patch } }));
      },
    }),
    {
      name: 'kotonebot-devtools2-preferences',
      onRehydrateStorage: () => (state) => {
        if (state?.language) {
          applyLanguage(state.language as LanguageOption);
        }
      },
    },
  ),
);
