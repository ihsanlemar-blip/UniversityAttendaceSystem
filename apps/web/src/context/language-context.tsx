'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { SupportedLocale, TextDirection, SUPPORTED_LOCALES, TranslationKey } from '../lib/i18n/types';
import { enTranslations } from '../lib/i18n/translations/en';
import { faAfTranslations } from '../lib/i18n/translations/fa-AF';
import { psTranslations } from '../lib/i18n/translations/ps';
import { getLocalizedError, UserSafeError } from '../lib/i18n/error-map';

interface LanguageContextType {
  locale: SupportedLocale;
  dir: TextDirection;
  isRtl: boolean;
  setLocale: (locale: SupportedLocale) => void;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
  getSafeError: (code: string) => UserSafeError;
}

const DICTIONARIES = {
  en: enTranslations,
  'fa-AF': faAfTranslations,
  ps: psTranslations,
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<SupportedLocale>(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem('dsas_locale') as SupportedLocale | null;
        if (saved && (saved === 'en' || saved === 'fa-AF' || saved === 'ps')) {
          return saved;
        }
      } catch {
        // localStorage not available
      }
    }
    return 'en';
  });

  // Keep HTML document lang and dir synchronized with current locale
  useEffect(() => {
    try {
      document.documentElement.lang = locale;
      document.documentElement.dir = SUPPORTED_LOCALES[locale].direction;
    } catch {
      // DOM access safety
    }
  }, [locale]);

  const setLocale = useCallback((newLocale: SupportedLocale) => {
    setLocaleState(newLocale);
    try {
      localStorage.setItem('dsas_locale', newLocale);
    } catch {
      // ignore storage error
    }
  }, []);

  const t = useCallback(
    (key: TranslationKey, params?: Record<string, string | number>): string => {
      const dict = DICTIONARIES[locale] || DICTIONARIES.en;
      let text = dict[key] || DICTIONARIES.en[key] || key;

      if (params) {
        Object.entries(params).forEach(([k, v]) => {
          text = text.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
        });
      }
      return text;
    },
    [locale]
  );

  const getSafeError = useCallback(
    (code: string): UserSafeError => {
      return getLocalizedError(code, locale);
    },
    [locale]
  );

  const dir: TextDirection = SUPPORTED_LOCALES[locale]?.direction || 'ltr';
  const isRtl = dir === 'rtl';

  return (
    <LanguageContext.Provider value={{ locale, dir, isRtl, setLocale, t, getSafeError }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextType {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}
