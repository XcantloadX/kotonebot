import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import en from './locales/en.json';
import zhCN from './locales/zh-CN.json';

export const SUPPORTED_LANGUAGES = ['en', 'zh-CN'] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

export const LANGUAGE_OPTIONS = ['system', ...SUPPORTED_LANGUAGES] as const;
export type LanguageOption = (typeof LANGUAGE_OPTIONS)[number];

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      'zh-CN': { translation: zhCN },
    },
    fallbackLng: 'en',
    supportedLngs: SUPPORTED_LANGUAGES,
    detection: {
      order: ['navigator'],
      caches: [],
    },
    interpolation: {
      escapeValue: false,
    },
  });

export function resolveSystemLanguage(): SupportedLanguage {
  const detected = i18n.language;
  if (SUPPORTED_LANGUAGES.includes(detected as SupportedLanguage)) {
    return detected as SupportedLanguage;
  }
  return 'en';
}

export default i18n;
