/**
 * Telegram Mini App (WebApp) integration.
 *
 * The app can be opened inside Telegram as a Mini App. In that case
 * Telegram passes signed `initData` that the backend uses to recognize
 * the user without a password. Here we:
 *  - detect that we are running inside Telegram;
 *  - load the official SDK only in that environment (a regular browser
 *    doesn't need the extra script);
 *  - tint the header/background to the Telegram theme so the webapp doesn't look out of place.
 *
 * In a regular browser every function is a no-op; app behavior is unchanged.
 */

/** Minimal type for the official SDK: only what we use. */
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

/** Colors match the app theme (index.html): dark and light. */
const DARK_BG = '#080b0a'
const LIGHT_BG = '#eef2f1'

/** Whether we are running inside the Telegram client (not a regular browser). */
export function isTelegramEnv(): boolean {
  if (typeof window === 'undefined') return false
  if (window.Telegram?.WebApp?.initData) return true
  if ('TelegramWebviewProxy' in window) return true
  if (window.location.hash.includes('tgWebAppData')) return true
  return /Telegram/i.test(navigator.userAgent)
}

let loadPromise: Promise<TelegramWebApp | null> | null = null

/**
 * Loads the Telegram SDK and returns the WebApp object (or null outside Telegram /
 * on load failure). The result is cached — repeated calls don't hit the network.
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

/** Tell Telegram the app is ready, expand to full height and tint the background. */
export function initTelegramWebApp(wa: TelegramWebApp): void {
  try {
    wa.ready()
    wa.expand()
    // Swiping down inside a Mini App closes the window — disable it so list scroll isn't lost.
    wa.disableVerticalSwipes?.()
    const bg = wa.colorScheme === 'light' ? LIGHT_BG : DARK_BG
    wa.setHeaderColor?.(bg)
    wa.setBackgroundColor?.(bg)
  } catch {
    // Styling is not critical: on error the app keeps working as is.
  }
}
