/** Admin panel: users. */
import { request } from './client'
import type { AdminUserDto, AdminUserPageDto, AdminUserUpdate } from './types'

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
