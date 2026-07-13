import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import i18n, { resolveSystemLanguage, LanguageOption } from '../i18n';

interface PreferencesState {
  language: LanguageOption;
  setLanguage: (lang: LanguageOption) => void;
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
      setLanguage: (lang) => {
        applyLanguage(lang);
        set({ language: lang });
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
