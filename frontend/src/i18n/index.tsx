/**
 * Minimal i18n with no external dependencies.
 *
 * - Russian and English dictionaries (~130 keys for the reference screens);
 * - parameters via {name};
 * - language choice stored in localStorage, default — browser language (ru → ru, otherwise en);
 * - <html lang> is kept in sync.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { ru } from './locales/ru'
import { en } from './locales/en'

export type Locale = 'ru' | 'en'
export type TranslationKey = keyof typeof ru
export type Translations = Record<TranslationKey, string>

const DICTIONARIES: Record<Locale, Translations> = { ru, en }
const STORAGE_KEY = 'bt-locale'

interface I18nValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: (key: TranslationKey, vars?: Record<string, string | number>) => string
  number: (value: number, options?: Intl.NumberFormatOptions) => string
}

const I18nContext = createContext<I18nValue | null>(null)

function detectLocale(): Locale {
  if (typeof window === 'undefined') return 'ru'
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'ru' || stored === 'en') return stored
  } catch {
    /* ignore */
  }
  const nav = window.navigator?.language ?? 'ru'
  return nav.toLowerCase().startsWith('ru') ? 'ru' : 'en'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(detectLocale)

  useEffect(() => {
    document.documentElement.lang = locale
    try {
      localStorage.setItem(STORAGE_KEY, locale)
    } catch {
      /* ignore */
    }
  }, [locale])

  const setLocale = useCallback((next: Locale) => setLocaleState(next), [])

  const t = useCallback(
    (key: TranslationKey, vars?: Record<string, string | number>) => {
      const dict = DICTIONARIES[locale]
      const template = dict[key] ?? DICTIONARIES.ru[key] ?? String(key)
      if (!vars) return template
      return template.replace(/\{(\w+)\}/g, (_, name: string) => String(vars[name] ?? `{${name}}`))
    },
    [locale],
  )

  const number = useCallback(
    (value: number, options?: Intl.NumberFormatOptions) =>
      new Intl.NumberFormat(locale === 'ru' ? 'ru-RU' : 'en-US', options).format(value),
    [locale],
  )

  const value = useMemo<I18nValue>(
    () => ({ locale, setLocale, t, number }),
    [locale, setLocale, t, number],
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nValue {
  const context = useContext(I18nContext)
  if (!context) throw new Error('useI18n должен вызываться внутри I18nProvider')
  return context
}
