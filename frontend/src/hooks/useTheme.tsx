import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

export type ThemeMode = 'light' | 'dark' | 'system'
export type ResolvedTheme = 'light' | 'dark'

const STORAGE_KEY = 'bt-theme'

interface ThemeValue {
  mode: ThemeMode
  resolved: ResolvedTheme
  /** есть для обратной совместимости со старыми вызовами */
  isDark: boolean
  setMode: (mode: ThemeMode) => void
}

const ThemeContext = createContext<ThemeValue | null>(null)

/** ?theme=light|dark|system — приоритетнее localStorage (нужно для QA-скриншотов). */
function readUrlMode(): ThemeMode | null {
  if (typeof window === 'undefined') return null
  const value = new URLSearchParams(window.location.search).get('theme')
  return value === 'light' || value === 'dark' || value === 'system' ? value : null
}

function readStoredMode(): ThemeMode {
  if (typeof window === 'undefined') return 'system'
  const fromUrl = readUrlMode()
  if (fromUrl) return fromUrl
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === 'light' || raw === 'dark' || raw === 'system') return raw
    // миграция со старого ключа 'theme'
    const legacy = localStorage.getItem('theme')
    if (legacy === 'light' || legacy === 'dark') return legacy
  } catch {
    /* приватный режим */
  }
  return 'system'
}

function systemPrefersDark(): boolean {
  if (typeof window === 'undefined' || !window.matchMedia) return true
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(readStoredMode)
  const [systemDark, setSystemDark] = useState<boolean>(systemPrefersDark)

  // «Как в браузере» должен реагировать на смену системной темы живьём
  useEffect(() => {
    if (!window.matchMedia) return
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = (event: MediaQueryListEvent) => setSystemDark(event.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  const resolved: ResolvedTheme = mode === 'system' ? (systemDark ? 'dark' : 'light') : mode

  useEffect(() => {
    const root = document.documentElement
    root.classList.toggle('dark', resolved === 'dark')
    root.dataset.theme = mode
    root.style.colorScheme = resolved
    if (!readUrlMode()) {
      try {
        localStorage.setItem(STORAGE_KEY, mode)
      } catch {
        /* игнорируем */
      }
    }
  }, [mode, resolved])

  const setMode = useCallback((next: ThemeMode) => setModeState(next), [])
  const value = useMemo<ThemeValue>(
    () => ({ mode, resolved, isDark: resolved === 'dark', setMode }),
    [mode, resolved, setMode],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeValue {
  const context = useContext(ThemeContext)
  if (!context) throw new Error('useTheme должен вызываться внутри ThemeProvider')
  return context
}
