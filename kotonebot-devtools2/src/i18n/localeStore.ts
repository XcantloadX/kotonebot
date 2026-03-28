import { create } from 'zustand';
import i18n, { SupportedLanguage, SUPPORTED_LANGUAGES } from './index';

interface LocaleState {
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
}

export const useLocaleStore = create<LocaleState>((set) => {
  const savedLang = i18n.language;
  const initialLang = SUPPORTED_LANGUAGES.includes(savedLang as SupportedLanguage)
    ? (savedLang as SupportedLanguage)
    : 'zh-CN';

  return {
    language: initialLang,
    setLanguage: (lang: SupportedLanguage) => {
      i18n.changeLanguage(lang);
      set({ language: lang });
    },
  };
});
