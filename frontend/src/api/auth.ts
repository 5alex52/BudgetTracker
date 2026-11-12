/** Authentication and session. */
import { request } from './client'
import type { TokenDto, UserDto } from './types'

/**
 * Login with username and password.
 *
 * The backend expects `application/x-www-form-urlencoded` (OAuth2) and puts the token
 * into an httpOnly cookie — so nothing needs to be stored in the browser.
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

/**
 * Login via Telegram Mini App: the backend verifies the `initData` signature with the bot
 * token and issues a session for the linked telegram_id. Tokens go into httpOnly cookies.
 */
export function telegramLogin(initData: string): Promise<TokenDto> {
  return request<TokenDto>('/auth/telegram', {
    method: 'POST',
    body: { init_data: initData },
    skipAuthRedirect: true,
    skipAuthRefresh: true,
  })
}

/** Current user: used to restore the session on load. */
export function me(): Promise<UserDto> {
  return request<UserDto>('/users/me', { skipAuthRedirect: true })
}

/** Registration: the backend creates the user, a default account and a set of categories. */
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

/** Confirm the address via the link from the email. */
export function verifyEmail(token: string): Promise<{ message: string }> {
  return request<{ message: string }>('/auth/verify-email', {
    method: 'POST',
    query: { token },
    skipAuthRedirect: true,
    skipAuthRefresh: true,
  })
}

/** Resend the confirmation email. */
export function resendVerification(email: string): Promise<{ message: string }> {
  return request<{ message: string }>('/auth/send-verification-email', {
    method: 'POST',
    query: { user_email: email },
    skipAuthRedirect: true,
    skipAuthRefresh: true,
  })
}

/** Login via an external service: link to the provider (github). */
export function oauthStartUrl(provider: 'github'): string {
  const base = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'
  return `${base.replace(/\/$/, '')}/auth/oauth/${provider}`
}
