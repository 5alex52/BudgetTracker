/** Трекер подписок на сервисы: список с итогом в базовой валюте, CRUD. */
import { request } from './client'
import type {
  ServiceSubCreatePayload,
  ServiceSubDto,
  ServiceSubListDto,
  ServiceSubUpdatePayload,
} from './types'

export function listServiceSubs(): Promise<ServiceSubListDto> {
  return request<ServiceSubListDto>('/finance/service-subs')
}

export function createServiceSub(payload: ServiceSubCreatePayload): Promise<ServiceSubDto> {
  return request<ServiceSubDto>('/finance/service-subs', { method: 'POST', body: payload })
}

export function updateServiceSub(id: number, payload: ServiceSubUpdatePayload): Promise<ServiceSubDto> {
  return request<ServiceSubDto>(`/finance/service-subs/${id}`, { method: 'PATCH', body: payload })
}

export function deleteServiceSub(id: number): Promise<void> {
  return request<void>(`/finance/service-subs/${id}`, { method: 'DELETE' })
}
