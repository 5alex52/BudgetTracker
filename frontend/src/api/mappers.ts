/**
 * Перевод ответов backend в UI-модели.
 *
 * Здесь же собраны «косметические» правила, которых в API нет: цвет маркера
 * счёта, иконка категории по умолчанию, знак суммы. Логика одна на всё
 * приложение, поэтому список, детали и графики выглядят одинаково.
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

/** Палитра маркеров счетов: тем же набором красится иконка в списке. */
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

/** Цвет категории, если пользователь его не выбрал. */
export const DEFAULT_CATEGORY_COLOR = '#7d8a86'
/** Иконка категории, если пользователь её не выбрал. */
export const DEFAULT_CATEGORY_ICON = 'circle'
export const TRANSFER_ICON = 'arrow-left-right'

const TINTS_KEY = 'bt-account-tints'

/**
 * Маркер счёта хранится только на клиенте (такого поля в API нет).
 * Выбор цвета детерминирован по id, а ручной выбор пользователя запоминается
 * в localStorage, чтобы карточки не перекрашивались при каждой загрузке.
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
    /* приватный режим — просто не запоминаем */
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

/** Плоский список из дерева: подкатегории нужны и вне дерева (форма записи). */
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

/** Подкатегории в форме записи: «родитель → дети» одним плоским списком. */
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

/** ISO-дата сервера → дата, время и исходная строка. */
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

/** Сумма со знаком: расход и перевод вычитаются, доход прибавляется. */
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

/* ------------------------------- графики -------------------------------- */

/** Подпись точки на оси: «11 окт.» — компактно и переводимо через Intl. */
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

/** Строки отчёта «категории × месяцы»: суммы расходов со знаком минус. */
export function toAnalyticsRows(matrix: MatrixDto): { months: string[]; rows: AnalyticsRow[] } {
  return {
    months: matrix.months,
    rows: matrix.rows.map((row) => ({
      id: String(row.category_id ?? row.name),
      name: row.name,
      icon: row.icon || undefined,
      color: row.color || undefined,
      values: row.values.map((value) => (value > 0 ? -value : value)),
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

/** «Месяц год» из ключа `2025-10`. */
export function monthLabel(key: string, locale: 'ru' | 'en'): string {
  const parsed = new Date(`${key}-01T00:00:00`)
  if (Number.isNaN(parsed.getTime())) return key
  return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
    month: 'long',
    year: 'numeric',
  }).format(parsed)
}

/** Точки денежного потока для графика на дашборде (только расход и доход). */
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
