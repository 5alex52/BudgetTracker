import { create } from 'zustand'
import { ApiError } from '@/api'
import * as authApi from '@/api/auth'
import type { UserDto } from '@/api/types'
import { initTelegramWebApp, loadTelegramWebApp } from '@/__shared__/utils/telegram'

/**
 * User session.
 *
 * The token lives in an httpOnly cookie, so "session restoration" is a request
 * to `/users/me`: if it answers, the user is logged in. We keep no tokens in
 * localStorage — the cookie can't be read from JS, and that's how it should be.
 */
type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

interface AuthState {
  user: UserDto | null
  status: AuthStatus
  error: string | null
  /** Session check at app startup */
  bootstrap: () => Promise<void>
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  /** Update the profile after editing settings */
  setUser: (user: UserDto) => void
  /** Local logout: called by the API client on 401 */
  clear: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  status: 'loading',
  error: null,

  bootstrap: async () => {
    set({ status: 'loading', error: null })
    // Inside a Telegram Mini App we boot the SDK and tint the window to the client theme.
    const webApp = await loadTelegramWebApp()
    if (webApp) initTelegramWebApp(webApp)
    try {
      const user = await authApi.me()
      set({ user, status: 'authenticated', error: null })
    } catch (caught) {
      const unauthorized = caught instanceof ApiError && caught.status === 401
      // No session, but we're in Telegram and have signed initData — log in with it.
      if (unauthorized && webApp?.initData) {
        try {
          await authApi.telegramLogin(webApp.initData)
          const user = await authApi.me()
          set({ user, status: 'authenticated', error: null })
          return
        } catch {
          // The account isn't linked or initData is invalid — show the regular login.
          set({ user: null, status: 'anonymous', error: null })
          return
        }
      }
      // 401 is the normal "not logged in" case; anything else is shown as error text
      const error = caught instanceof ApiError && !unauthorized ? caught.detail : null
      set({ user: null, status: 'anonymous', error })
    }
  },

  signIn: async (email, password) => {
    set({ error: null })
    try {
      await authApi.login(email, password)
      const user = await authApi.me()
      set({ user, status: 'authenticated', error: null })
    } catch (caught) {
      const error = caught instanceof ApiError ? caught.detail : String(caught)
      set({ status: 'anonymous', error })
      throw caught
    }
  },

  signOut: async () => {
    try {
      await authApi.logout()
    } catch {
      // The session may have already expired: we still need to log out
    }
    set({ user: null, status: 'anonymous', error: null })
  },

  setUser: (user) => set({ user, status: 'authenticated' }),
  clear: () => set({ user: null, status: 'anonymous', error: null }),
}))
