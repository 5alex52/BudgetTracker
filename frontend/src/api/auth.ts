/** Авторизация и сессия. */
import { request } from './client'
import type { TokenDto, UserDto } from './types'

/**
 * Вход по логину и паролю.
 *
 * Backend ждёт `application/x-www-form-urlencoded` (OAuth2), а токен кладёт
 * в httpOnly-cookie — поэтому в браузере ничего сохранять не нужно.
 */
export function login(email: string, password: string): Promise<TokenDto> {
  return request<TokenDto>('/auth/login', {
    method: 'POST',
    form: { username: email.trim(), password },
    skipAuthRedirect: true,
    skipAuthRefresh: true,
  })
}

export function logout(): Promise<void> {
  return request<void>('/auth/logout', { method: 'POST', skipAuthRedirect: true, skipAuthRefresh: true })
}

export function refresh(): Promise<TokenDto> {
  return request<TokenDto>('/auth/refresh', { method: 'POST', skipAuthRedirect: true, skipAuthRefresh: true })
}

/** Текущий пользователь: используется для восстановления сессии при загрузке. */
export function me(): Promise<UserDto> {
  return request<UserDto>('/users/me', { skipAuthRedirect: true })
}

/** Регистрация: backend создаёт пользователя, счёт по умолчанию и набор категорий. */
export function register(payload: {
  firstname: string
  lastname: string
  email: string
  password: string
}): Promise<UserDto> {
  return request<UserDto>('/auth/register', {
    method: 'POST',
    body: payload,
    skipAuthRedirect: true,
    skipAuthRefresh: true,
  })
}

/** Подтверждение адреса по ссылке из письма. */
export function verifyEmail(token: string): Promise<{ message: string }> {
  return request<{ message: string }>('/auth/verify-email', {
    method: 'POST',
    query: { token },
    skipAuthRedirect: true,
    skipAuthRefresh: true,
  })
}

/** Повторная отправка письма подтверждения. */
export function resendVerification(email: string): Promise<{ message: string }> {
  return request<{ message: string }>('/auth/send-verification-email', {
    method: 'POST',
    query: { user_email: email },
    skipAuthRedirect: true,
    skipAuthRefresh: true,
  })
}

/** Вход через внешний сервис: ссылка на провайдера (github). */
export function oauthStartUrl(provider: 'github'): string {
  const base = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'
  return `${base.replace(/\/$/, '')}/auth/oauth/${provider}`
}
