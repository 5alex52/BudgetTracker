/** Тарифы, подписка, способы оплаты и история платежей. */
import { request } from './client'
import type {
  CheckoutSessionDto,
  EntitlementsDto,
  PaymentDto,
  PaymentMethodDto,
  PlanDto,
  ProviderInfoDto,
  SubscriptionDto,
} from './types'

export function listPlans(): Promise<PlanDto[]> {
  return request<PlanDto[]>('/billing/plans')
}

export function listProviders(): Promise<ProviderInfoDto[]> {
  return request<ProviderInfoDto[]>('/billing/providers')
}

export function getSubscription(): Promise<SubscriptionDto> {
  return request<SubscriptionDto>('/billing/subscription')
}

/** Лимиты тарифа: сколько счетов можно, доступны ли валюты и премиум-виджеты. */
export function getEntitlements(): Promise<EntitlementsDto> {
  return request<EntitlementsDto>('/billing/entitlements')
}

/** Оформление подписки: mock подтверждает сразу, реальный провайдер вернёт checkout_url. */
export function changeSubscription(planCode: string, provider?: string): Promise<CheckoutSessionDto> {
  return request<CheckoutSessionDto>('/billing/subscription', {
    method: 'POST',
    body: { plan_code: planCode, provider },
  })
}

export function cancelSubscription(immediately = false): Promise<SubscriptionDto> {
  return request<SubscriptionDto>('/billing/subscription', {
    method: 'DELETE',
    query: { immediately },
  })
}

export function listPaymentMethods(): Promise<PaymentMethodDto[]> {
  return request<PaymentMethodDto[]>('/billing/payment-methods')
}

/** Токен от платёжной формы; данные карты на backend не попадают. */
export function attachPaymentMethod(payload: {
  provider?: string
  kind?: 'card' | 'crypto' | 'bank_transfer'
  token?: string
  makeDefault?: boolean
}): Promise<PaymentMethodDto> {
  return request<PaymentMethodDto>('/billing/payment-methods', {
    method: 'POST',
    body: {
      provider: payload.provider,
      kind: payload.kind ?? 'card',
      token: payload.token,
      make_default: payload.makeDefault ?? false,
    },
  })
}

export function makePaymentMethodDefault(methodId: number): Promise<PaymentMethodDto> {
  return request<PaymentMethodDto>(`/billing/payment-methods/${methodId}/default`, { method: 'POST' })
}

export function deletePaymentMethod(methodId: number): Promise<void> {
  return request<void>(`/billing/payment-methods/${methodId}`, { method: 'DELETE' })
}

export function listPayments(limit = 50): Promise<PaymentDto[]> {
  return request<PaymentDto[]>('/billing/payments', { query: { limit } })
}
