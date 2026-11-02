/** Профиль пользователя: настройки, смена пароля, выгрузка и удаление аккаунта. */
import { request } from './client'
import type { UserDto, UserExportDto, UserProfileUpdate } from './types'

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

/** Удаление аккаунта требует пароль: сервер не должен удалять данные «по клику». */
export function deleteAccount(password: string): Promise<void> {
  return request<void>('/users/me', { method: 'DELETE', body: { password } })
}
