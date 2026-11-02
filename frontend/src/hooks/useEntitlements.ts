/**
 * Права пользователя по тарифу.
 *
 * Одна точка для лимитов: и настройки, и «Обзор» читают одно и то же,
 * поэтому платные виджеты появляются сразу после оплаты, а не «когда-нибудь
 * после перезагрузки».
 */
import { billingApi } from '@/api'
import { useApiQuery, type QueryState } from '@/hooks/useApi'
import type { EntitlementsDto } from '@/api/types'

export type Entitlements = EntitlementsDto

export function useEntitlements(): QueryState<Entitlements> {
  return useApiQuery(() => billingApi.getEntitlements(), [])
}

/** Мягкий доступ к флагам: пока ответ не пришёл, считаем всё бесплатным. */
export function useIsPremium(): boolean {
  const { data } = useEntitlements()
  return data?.advanced_analytics === true
}
