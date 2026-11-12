/**
 * Mapping backend responses to UI models.
 *
 * Also collects the "cosmetic" rules the API doesn't have: account marker color,
 * default category icon, amount sign. One logic for the whole app, so lists,
 * details and charts look consistent.
 */
import type {
  AccountDto,
  AccountShareDto,
  CategoryDto,
  CategoryNodeDto,
  CategoryShareDto,
  CurrencyRateDto,
  MatrixDto,
  SeriesPointDto,
  TemplateDto,
  TimeseriesDto,
  TransactionWithDetailsDto,
} from '@/api/types'
import type {
  Account,
  AnalyticsRow,
  Category,
  CurrencyRate,
  RecordItem,
  Subcategory,
} from '@/__shared__/types/models'

/** Account marker palette: the same set colors the icon in the list. */
export const ACCOUNT_TINTS = [
  '#d94b4b',
  '#e06fa0',
  '#e08a3c',
  '#3aa76d',
  '#2ba7d6',
  '#5b8fd6',
  '#8b6fd6',
  '#c26bd6',
]

/** Category color when the user hasn't picked one. */
export const DEFAULT_CATEGORY_COLOR = '#7d8a86'
/** Category icon when the user hasn't picked one. */
export const DEFAULT_CATEGORY_ICON = 'circle'
export const TRANSFER_ICON = 'arrow-left-right'

const TINTS_KEY = 'bt-account-tints'

/**
 * The account marker is stored on the client only (the API has no such field).
 * Color choice is deterministic by id, and the user's manual pick is remembered
 * in localStorage so cards don't get repainted on every load.
 */
function readTintOverrides(): Record<string, string> {
  try {
    const raw = localStorage.getItem(TINTS_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as Record<string, string>
    return parsed && typeof parsed === 'object' ? parsed : {}
  } catch {
    return {}
  }
}

export function saveAccountTint(accountId: string, tint: string) {
  try {
    localStorage.setItem(TINTS_KEY, JSON.stringify({ ...readTintOverrides(), [accountId]: tint }))
  } catch {
    /* private mode — just don't remember */
  }
}

export function accountTint(accountId: string | number): string {
  const key = String(accountId)
  const override = readTintOverrides()[key]
  if (override) return override
  let hash = 0
  for (let index = 0; index < key.length; index += 1) {
    hash = (hash * 31 + key.charCodeAt(index)) % 100000
  }
  return ACCOUNT_TINTS[hash % ACCOUNT_TINTS.length]
}

export function toAccount(dto: AccountDto): Account {
  return {
    id: String(dto.id),
    name: dto.name,
    kind: dto.type,
    balance: dto.balance,
    currency: dto.currency_id,
    tint: accountTint(dto.id),
    excluded: dto.is_excluded,
    archived: dto.is_archived,
    crypto: dto.crypto_kind != null,
  }
}

export function toCategory(dto: CategoryDto): Category {
  return {
    id: dto.id,
    name: dto.name,
    icon: dto.icon || DEFAULT_CATEGORY_ICON,
    color: dto.color || DEFAULT_CATEGORY_COLOR,
    type: dto.type,
    parentId: dto.parent_id,
  }
}

/** Flat list from the tree: subcategories are needed outside the tree too (record form). */
export function flattenTree(nodes: CategoryNodeDto[], type?: Category['type']): Category[] {
  const result: Category[] = []
  const walk = (items: CategoryNodeDto[]) => {
    items.forEach((node) => {
      result.push({
        id: node.id,
        name: node.name,
        icon: node.icon || DEFAULT_CATEGORY_ICON,
        color: node.color || DEFAULT_CATEGORY_COLOR,
        type: node.type,
        parentId: node.parent_id,
        transactionsCount: node.transactions_count,
        children: node.children?.length ? [] : undefined,
      })
      if (node.children?.length) walk(node.children)
    })
  }
  walk(nodes)
  return type ? result.filter((item) => item.type === type) : result
}

export function toCategoryTree(nodes: CategoryNodeDto[]): Category[] {
  return nodes.map((node) => ({
    id: node.id,
    name: node.name,
    icon: node.icon || DEFAULT_CATEGORY_ICON,
    color: node.color || DEFAULT_CATEGORY_COLOR,
    type: node.type,
    parentId: node.parent_id,
    transactionsCount: node.transactions_count,
    children: toCategoryTree(node.children ?? []),
  }))
}

/** Subcategories in the record form: "parent → children" as one flat list. */
export function toSubcategories(categories: Category[]): Subcategory[] {
  return categories
    .filter((category) => category.parentId !== null)
    .map((category) => ({
      id: category.id,
      name: category.name,
      parent: category.parentId,
      icon: category.icon,
      color: category.color,
      type: category.type,
    }))
}

/** Server ISO date → date, time and the original string. */
export function splitDateTime(iso: string): { date: string; time: string; iso: string } {
  if (!iso) return { date: '', time: '', iso: '' }
  const parsed = new Date(iso.length <= 10 ? `${iso}T00:00:00` : iso)
  if (Number.isNaN(parsed.getTime())) {
    return { date: iso.slice(0, 10), time: '00:00', iso }
  }
  const pad = (value: number) => String(value).padStart(2, '0')
  return {
    date: `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())}`,
    time: `${pad(parsed.getHours())}:${pad(parsed.getMinutes())}`,
    iso,
  }
}

/** Signed amount: expense and transfer are subtracted, income is added. */
export function signedAmount(type: string, amount: number): number {
  const abs = Math.abs(amount)
  return type === 'income' ? abs : -abs
}

export interface RecordLookup {
  accounts: Map<number, Account>
}

export function toRecordItem(dto: TransactionWithDetailsDto, lookup?: RecordLookup): RecordItem {
  const { date, time, iso } = splitDateTime(dto.date)
  const account = lookup?.accounts.get(dto.account_id)
  return {
    id: String(dto.id),
    type: dto.type,
    categoryId: dto.category_id,
    category: dto.category_name,
    categoryIcon: dto.category_icon || DEFAULT_CATEGORY_ICON,
    categoryColor: dto.category_color || DEFAULT_CATEGORY_COLOR,
    accountId: String(dto.account_id),
    account: dto.account_name,
    accountTint: account?.tint ?? accountTint(dto.account_id),
    transferAccountId: dto.transfer_account_id ? String(dto.transfer_account_id) : undefined,
    transferAccount: dto.transfer_account_name ?? undefined,
    amount: signedAmount(dto.type, dto.amount),
    currency: dto.currency_id,
    date,
    time,
    iso,
    note: dto.note ?? undefined,
    tags: (dto.tags ?? []).map((tag) => ({ id: tag.id, name: tag.name, color: tag.color })),
    isExcluded: dto.is_excluded,
  }
}

export function toCurrencyRate(dto: CurrencyRateDto): CurrencyRate {
  return {
    code: dto.code,
    name: dto.name,
    symbol: dto.symbol,
    rate: dto.rate,
    base: dto.is_base,
    custom: dto.is_custom,
  }
}

/* ------------------------------- charts ---------------------------------- */

/** Axis point label: "Oct 11" — compact and localizable via Intl. */
export function pointLabel(iso: string, locale: 'ru' | 'en'): string {
  const parsed = new Date(iso.length <= 10 ? `${iso}T00:00:00` : iso)
  if (Number.isNaN(parsed.getTime())) return iso
  return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
    day: 'numeric',
    month: 'short',
  }).format(parsed)
}

export function toBalancePoints(timeseries: TimeseriesDto, locale: 'ru' | 'en') {
  return timeseries.points.map((point) => ({
    label: pointLabel(point.date, locale),
    value: point.value ?? 0,
  }))
}

export function toCashflowPoints(timeseries: TimeseriesDto, locale: 'ru' | 'en') {
  return timeseries.points.map((point) => ({
    label: pointLabel(point.date, locale),
    income: point.income ?? 0,
    expense: -(Math.abs(point.expense ?? 0)),
  }))
}

export function toDonutSegments(items: CategoryShareDto[], limit = 5) {
  return items.slice(0, limit).map((item) => ({
    name: item.name,
    value: Math.abs(item.total),
    color: item.color || DEFAULT_CATEGORY_COLOR,
  }))
}

/** Bars for the column chart: category + amount + color. */
export function toBarSegments(items: CategoryShareDto[], limit = 8) {
  return items.slice(0, limit).map((item) => ({
    label: item.name,
    value: Math.abs(item.total),
    color: item.color || DEFAULT_CATEGORY_COLOR,
    transactionsCount: item.transactions_count,
  }))
}

/** Rows of the "categories × months" report: expense amounts with a minus sign. */
/**
 * The "categories × months" matrix.
 *
 * The backend always returns absolute values ( amount_base ≥ 0 ). For expenses
 * the _UI_ shows them with a "−" sign so it's visible that money is going out.
 * Income stays positive — otherwise the income report would look like
 * a loss.
 */
export function toAnalyticsRows(
  matrix: MatrixDto,
  txType?: 'expense' | 'income',
): { months: string[]; rows: AnalyticsRow[] } {
  return {
    months: matrix.months,
    rows: matrix.rows.map((row) => ({
      id: String(row.category_id ?? row.name),
      name: row.name,
      icon: row.icon || undefined,
      color: row.color || undefined,
      values:
        txType === 'expense'
          ? row.values.map((value) => (value > 0 ? -value : value))
          : row.values,
      trends: row.trends,
    })),
  }
}

export function toAccountShares(items: AccountShareDto[]) {
  return items.map((item) => ({
    ...item,
    tint: accountTint(item.account_id),
  }))
}

/** "Month year" from a `2025-10` key. */
export function monthLabel(key: string, locale: 'ru' | 'en'): string {
  const parsed = new Date(`${key}-01T00:00:00`)
  if (Number.isNaN(parsed.getTime())) return key
  return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
    month: 'long',
    year: 'numeric',
  }).format(parsed)
}

/** Cashflow points for the dashboard chart (expense and income only). */
export function seriesToPoints(points: SeriesPointDto[], locale: 'ru' | 'en') {
  return points.map((point) => ({ label: pointLabel(point.date, locale), point }))
}

export function toTemplate(dto: TemplateDto) {
  return {
    id: dto.id,
    name: dto.name,
    type: dto.type,
    amount: dto.amount,
    currency: dto.currency_id,
    accountId: String(dto.account_id),
    categoryId: dto.category_id,
    note: dto.note ?? '',
    icon: dto.icon || 'bolt',
    usage: dto.usage_count,
    tags: dto.tags.map((tag) => tag.name),
  }
}
