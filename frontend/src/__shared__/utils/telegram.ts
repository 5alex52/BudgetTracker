/**
 * Telegram Mini App (WebApp) интеграция.
 *
 * Приложение может открываться внутри Telegram как Mini App. В этом случае
 * Telegram передаёт подписанные данные `initData`, по которым backend
 * опознаёт пользователя без пароля. Здесь мы:
 *  - определяем, что запущены внутри Telegram;
 *  - подгружаем официальный SDK только в этом окружении (в обычном браузере
 *    лишний скрипт не нужен);
 *  - красим шапку/фон под тему Telegram, чтобы webapp не «выпадал» из клиента.
 *
 * В обычном браузере все функции — no-op, поведение приложения не меняется.
 */

/** Минимальный тип официального SDK: только то, что используем. */
export interface TelegramWebApp {
  initData: string
  initDataUnsafe?: { user?: { id: number } }
  colorScheme?: 'light' | 'dark'
  ready: () => void
  expand: () => void
  setHeaderColor?: (color: string) => void
  setBackgroundColor?: (color: string) => void
  disableVerticalSwipes?: () => void
}

declare global {
  interface Window {
    Telegram?: { WebApp?: TelegramWebApp }
    TelegramWebviewProxy?: unknown
  }
}

const SDK_URL = 'https://telegram.org/js/telegram-web-app.js'

/** Цвета совпадают с темой приложения (index.html): тёмная и светлая. */
const DARK_BG = '#080b0a'
const LIGHT_BG = '#eef2f1'

/** Запущены ли мы внутри клиента Telegram (а не в обычном браузере). */
export function isTelegramEnv(): boolean {
  if (typeof window === 'undefined') return false
  if (window.Telegram?.WebApp?.initData) return true
  if ('TelegramWebviewProxy' in window) return true
  if (window.location.hash.includes('tgWebAppData')) return true
  return /Telegram/i.test(navigator.userAgent)
}

let loadPromise: Promise<TelegramWebApp | null> | null = null

/**
 * Подгружает SDK Telegram и возвращает объект WebApp (или null вне Telegram /
 * при ошибке загрузки). Результат кешируется — повторные вызовы не дёргают сеть.
 */
export function loadTelegramWebApp(): Promise<TelegramWebApp | null> {
  if (typeof window === 'undefined' || !isTelegramEnv()) {
    return Promise.resolve(null)
  }
  if (window.Telegram?.WebApp) {
    return Promise.resolve(window.Telegram.WebApp)
  }
  if (loadPromise) return loadPromise

  loadPromise = new Promise<TelegramWebApp | null>((resolve) => {
    const script = document.createElement('script')
    script.src = SDK_URL
    script.async = true
    script.onload = () => resolve(window.Telegram?.WebApp ?? null)
    script.onerror = () => resolve(null)
    document.head.appendChild(script)
  })
  return loadPromise
}

/** Сообщаем Telegram, что приложение готово, разворачиваем на всю высоту и красим фон. */
export function initTelegramWebApp(wa: TelegramWebApp): void {
  try {
    wa.ready()
    wa.expand()
    // Свайп вниз внутри Mini App закрывает окно — отключаем, чтобы не терять скролл списка.
    wa.disableVerticalSwipes?.()
    const bg = wa.colorScheme === 'light' ? LIGHT_BG : DARK_BG
    wa.setHeaderColor?.(bg)
    wa.setBackgroundColor?.(bg)
  } catch {
    // Оформление не критично: при ошибке приложение продолжает работать как есть.
  }
}
