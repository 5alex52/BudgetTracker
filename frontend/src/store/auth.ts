import { create } from 'zustand'
import { ApiError } from '@/api'
import * as authApi from '@/api/auth'
import type { UserDto } from '@/api/types'
import { initTelegramWebApp, loadTelegramWebApp } from '@/__shared__/utils/telegram'

/**
 * Сессия пользователя.
 *
 * Токен живёт в httpOnly-cookie, поэтому «восстановление сессии» — это запрос
 * `/users/me`: если он ответил, пользователь вошёл. Никаких токенов в
 * localStorage не держим — их нельзя прочитать из JS и это правильно.
 */
type AuthStatus = 'loading' | 'authenticated' | 'anonymous'

interface AuthState {
  user: UserDto | null
  status: AuthStatus
  error: string | null
  /** Проверка сессии при старте приложения */
  bootstrap: () => Promise<void>
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  /** Обновить профиль после правки настроек */
  setUser: (user: UserDto) => void
  /** Локальный разлогин: вызывается клиентом API при 401 */
  clear: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  status: 'loading',
  error: null,

  bootstrap: async () => {
    set({ status: 'loading', error: null })
    // Внутри Telegram Mini App поднимаем SDK и красим окно под тему клиента.
    const webApp = await loadTelegramWebApp()
    if (webApp) initTelegramWebApp(webApp)
    try {
      const user = await authApi.me()
      set({ user, status: 'authenticated', error: null })
    } catch (caught) {
      const unauthorized = caught instanceof ApiError && caught.status === 401
      // Нет сессии, но мы в Telegram и есть подписанные initData — входим по ним.
      if (unauthorized && webApp?.initData) {
        try {
          await authApi.telegramLogin(webApp.initData)
          const user = await authApi.me()
          set({ user, status: 'authenticated', error: null })
          return
        } catch {
          // Аккаунт не привязан или initData недействителен — показываем обычный вход.
          set({ user: null, status: 'anonymous', error: null })
          return
        }
      }
      // 401 — обычная ситуация «не вошёл»; остальное показываем текстом ошибки
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
      // Сессия могла уже истечь: выходить всё равно нужно
    }
    set({ user: null, status: 'anonymous', error: null })
  },

  setUser: (user) => set({ user, status: 'authenticated' }),
  clear: () => set({ user: null, status: 'anonymous', error: null }),
}))
