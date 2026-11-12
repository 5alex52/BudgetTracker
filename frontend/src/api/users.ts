/** User profile: settings, password change, account export and deletion. */
import { request } from './client'
import type {
  PushPublicKeyDto,
  PushSubscribeDto,
  TelegramLinkDto,
  UserDto,
  UserExportDto,
  UserProfileUpdate,
} from './types'

export function getProfile(): Promise<UserDto> {
  return request<UserDto>('/users/me')
}

export function updateProfile(payload: UserProfileUpdate): Promise<UserDto> {
  return request<UserDto>('/users/me', { method: 'PATCH', body: payload })
}

export function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  return request<void>('/users/me/password', {
    method: 'POST',
    body: { old_password: oldPassword, new_password: newPassword },
  })
}

export function exportAccountData(): Promise<UserExportDto> {
  return request<UserExportDto>('/users/me/export')
}

/** Account deletion requires a password: the server must not delete data "on a click". */
export function deleteAccount(password: string): Promise<void> {
  return request<void>('/users/me', { method: 'DELETE', body: { password } })
}

/* --------------------- notifications: Telegram + Web Push ------------------- */

export function getTelegramLink(): Promise<TelegramLinkDto> {
  return request<TelegramLinkDto>('/users/me/telegram/link')
}

export function unlinkTelegram(): Promise<void> {
  return request<void>('/users/me/telegram', { method: 'DELETE' })
}

export function getPushPublicKey(): Promise<PushPublicKeyDto> {
  return request<PushPublicKeyDto>('/users/me/push/public-key')
}

export function subscribePush(payload: PushSubscribeDto): Promise<void> {
  return request<void>('/users/me/push', { method: 'POST', body: payload })
}

export function unsubscribePush(endpoint: string): Promise<void> {
  return request<void>('/users/me/push', { method: 'DELETE', body: { endpoint } })
}
