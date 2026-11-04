/** Админ-панель: пользователи, статистика и ручное управление подписками. */
import { request } from './client'
import type {
  AdminStatsDto,
  AdminSubscriptionTimelineDto,
  AdminUserDto,
  AdminUserPageDto,
  AdminUserUpdate,
} from './types'

export function getAdminStats(): Promise<AdminStatsDto> {
  return request<AdminStatsDto>('/admin/stats')
}

export function getSubscriptionTimeline(days = 30): Promise<AdminSubscriptionTimelineDto> {
  return request<AdminSubscriptionTimelineDto>(`/admin/stats/subscriptions?days=${days}`)
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

export function grantAdminSubscription(id: string, planCode: string): Promise<AdminUserDto> {
  return request<AdminUserDto>(`/admin/users/${id}/subscription`, {
    method: 'POST',
    body: { plan_code: planCode },
  })
}

export function revokeAdminSubscription(id: string): Promise<AdminUserDto> {
  return request<AdminUserDto>(`/admin/users/${id}/subscription`, { method: 'DELETE' })
}
