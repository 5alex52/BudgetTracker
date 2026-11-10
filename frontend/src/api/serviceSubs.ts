/** Трекер подписок на сервисы: список с итогом в базовой валюте, CRUD, автосписания. */
import { request } from './client'
import type {
  ServiceSubCreatePayload,
  ServiceSubDto,
  ServiceSubListDto,
  ServiceSubMonthTotalDto,
  ServiceSubUpdatePayload,
} from './types'

export function listServiceSubs(): Promise<ServiceSubListDto> {
  return request<ServiceSubListDto>('/finance/service-subs')
}

/** Создаёт записи для подписок, у которых наступила дата списания. */
export function collectServiceSubs(): Promise<{ created: number }> {
  return request<{ created: number }>('/finance/service-subs/collect', { method: 'POST' })
}

export function getChargesSummary(months = 6): Promise<ServiceSubMonthTotalDto[]> {
  return request<ServiceSubMonthTotalDto[]>(`/finance/service-subs/charges-summary?months=${months}`)
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
