/**
 * UI-модели домена.
 *
 * Это не ответы сервера (они в `@/api/types`), а то, чем пользуются компоненты:
 * подписи, иконки, знак суммы, разложенные дата и время. Перевод одним слоем
 * мапперов держит компоненты независимыми от формы API.
 */
import type { AccountTypeValue, CategoryTypeValue, TransactionTypeValue } from '@/api/types'

export type Currency = string

/** Типы счетов сервиса: cash, checking, credit_card, savings, investment. */
export type AccountKind = AccountTypeValue

export interface Account {
  id: string
  name: string
  kind: AccountKind
  balance: number
  currency: Currency
  /** Цветовой маркер счёта (точка в списке записей, полоса карточки) */
  tint: string
  /** Исключён из статистики */
  excluded?: boolean
  archived?: boolean
  /** Криптокошелёк: баланс и валюта управляются синхронизацией со страницы «Крипто» */
  crypto?: boolean
  /** Данные доступны только на чтение */
  /** Почему счёт заблокирован: лимит или валюта тарифа */
}

export interface Category {
  id: number
  name: string
  /** Иконка lucide по имени из набора */
  icon: string
  color: string
  type: CategoryTypeValue
  parentId: number | null
  /** Сколько записей в категории (приходит из дерева/статистики) */
  transactionsCount?: number
  children?: Category[]
  hidden?: boolean
}

export interface RecordTag {
  id: number
  name: string
  color: string
}

export interface RecordItem {
  id: string
  type: TransactionTypeValue
  categoryId: number
  category: string
  categoryIcon: string
  categoryColor: string
  accountId: string
  account: string
  accountTint: string
  /** Счёт-получатель перевода */
  transferAccountId?: string
  transferAccount?: string
  /** Сумма со знаком: расход отрицательный, доход положительный */
  amount: number
  currency: Currency
  /** Дата в формате YYYY-MM-DD: по ней группируется список */
  date: string
  /** Время в формате HH:MM */
  time: string
  /** Полная дата-время ISO — нужна для отправки на сервер */
  iso: string
  note?: string
  payer?: string
  tags: RecordTag[]
  /** Запись не участвует в статистике (правило или ручная отметка) */
  isExcluded: boolean
}

/** Строка отчёта «категории × месяцы» */
export interface AnalyticsRow {
  id: string
  name: string
  icon?: string
  color?: string
  values: number[]
  trends: number[]
}

export interface CurrencyRate {
  code: string
  name: string
  symbol: string
  /** Курс к базовой валюте: 1 базовая = X этой валюты */
  rate: number
  base?: boolean
  /** Курс переопределён пользователем */
  custom?: boolean
}

export interface Subcategory {
  id: number
  name: string
  parent: number | null
  icon: string
  color: string
  type: CategoryTypeValue
}
