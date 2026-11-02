/** Валюты: справочник курсов и личные переопределения пользователя. */
import { request } from './client'
import type { CurrencyDto, CurrencyRateDto } from './types'

export function listCurrencies(): Promise<CurrencyDto[]> {
  return request<CurrencyDto[]>('/finance/currencies/', { query: { limit: 100 } })
}

/** Курсы относительно базовой валюты; для вошедшего пользователя — с личными курсами. */
export function getRates(base?: string): Promise<CurrencyRateDto[]> {
  return request<CurrencyRateDto[]>('/finance/currencies/rates', { query: { base } })
}

export function setUserRate(code: string, rate: number): Promise<CurrencyRateDto> {
  return request<CurrencyRateDto>(`/finance/currencies/${code}/rate`, {
    method: 'PUT',
    body: { rate },
  })
}

export function resetUserRate(code: string): Promise<void> {
  return request<void>(`/finance/currencies/${code}/rate`, { method: 'DELETE' })
}
