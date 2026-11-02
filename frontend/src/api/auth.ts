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
  })
}

export function logout(): Promise<void> {
  return request<void>('/auth/logout', { method: 'POST', skipAuthRedirect: true })
}

export function refresh(): Promise<TokenDto> {
  return request<TokenDto>('/auth/refresh', { method: 'POST', skipAuthRedirect: true })
}

/** Текущий пользователь: используется для восстановления сессии при загрузке. */
export function me(): Promise<UserDto> {
  return request<UserDto>('/users/me', { skipAuthRedirect: true })
}
