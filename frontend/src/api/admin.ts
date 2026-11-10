/** Админ-панель: пользователи и статистика. */
import { request } from './client'
import type {
  AdminStatsDto,
  AdminUserDto,
  AdminUserPageDto,
  AdminUserUpdate,
} from './types'

export function getAdminStats(): Promise<AdminStatsDto> {
  return request<AdminStatsDto>('/admin/stats')
}

export function listAdminUsers(params: {
  search?: string
  offset?: number
  limit?: number
}): Promise<AdminUserPageDto> {
  return request<AdminUserPageDto>('/admin/users', { query: params })
}

export function updateAdminUser(id: string, payload: AdminUserUpdate): Promise<AdminUserDto> {
  return request<AdminUserDto>(`/admin/users/${id}`, { method: 'PATCH', body: payload })
}
