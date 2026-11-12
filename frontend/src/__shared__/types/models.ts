/**
 * Domain UI models.
 *
 * Not server responses (those live in `@/api/types`) but what components use:
 * labels, icons, signed amounts, split date and time. A single mapper layer
 * keeps components independent of the API shape.
 */
import type { AccountTypeValue, CategoryTypeValue, TransactionTypeValue } from '@/api/types'

export type Currency = string

/** Account types supported by the service: cash, checking, credit_card, savings, investment. */
export type AccountKind = AccountTypeValue

export interface Account {
  id: string
  name: string
  kind: AccountKind
  balance: number
  currency: Currency
  /** Account color marker (dot in the records list, card stripe) */
  tint: string
  /** Excluded from statistics */
  excluded?: boolean
  archived?: boolean
  /** Crypto wallet: balance and currency are managed by sync from the Crypto page */
  crypto?: boolean
  /** Data is read-only */
  /** Why the account is locked: plan limit or currency */
}

export interface Category {
  id: number
  name: string
  /** Lucide icon by name from the set */
  icon: string
  color: string
  type: CategoryTypeValue
  parentId: number | null
  /** Number of records in the category (comes from the tree/statistics) */
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
  /** Transfer destination account */
  transferAccountId?: string
  transferAccount?: string
  /** Signed amount: expense is negative, income is positive */
  amount: number
  currency: Currency
  /** Date in YYYY-MM-DD format: the list is grouped by it */
  date: string
  /** Time in HH:MM format */
  time: string
  /** Full ISO date-time — needed for sending to the server */
  iso: string
  note?: string
  payer?: string
  tags: RecordTag[]
  /** Record is excluded from statistics (rule or manual flag) */
  isExcluded: boolean
}

/** Row of the "categories × months" report */
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
  /** Rate to the base currency: 1 base = X of this currency */
  rate: number
  base?: boolean
  /** Rate overridden by the user */
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
