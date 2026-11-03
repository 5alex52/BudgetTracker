/**
 * Типы ответов и запросов backend — ровно то, что описано в OpenAPI
 * (`/docs` backend-сервиса). Названия полей намеренно совпадают с сервером:
 * мапперы в UI-модели живут отдельно (см. `mappers.ts`), а здесь только контракт.
 */

export type TransactionTypeValue = 'income' | 'expense' | 'transfer'
export type CategoryTypeValue = 'income' | 'expense' | 'transfer'
export type AccountTypeValue = 'cash' | 'checking' | 'credit_card' | 'savings' | 'investment'
export type RuleFieldValue = 'note' | 'amount'
export type RuleOperatorValue = 'contains' | 'equals' | 'greater' | 'less'
export type PlanPeriodValue = 'none' | 'month' | 'year'
export type SubscriptionStatusValue = 'active' | 'canceled' | 'expired' | 'pending'
export type PaymentStatusValue = 'pending' | 'succeeded' | 'failed' | 'refunded'
export type PaymentKindValue = 'subscription' | 'one_time'
export type PaymentMethodKindValue = 'card' | 'crypto' | 'bank_transfer'

/* ------------------------------- профиль -------------------------------- */

export interface UserDto {
  id: string
  firstname: string | null
  lastname: string | null
  fullname: string
  email: string
  photo: string | null
  is_active: boolean
  is_verified: boolean
  is_superuser: boolean
  timezone: string | null
  base_currency: string | null
  locale: string | null
  theme: string | null
  default_period: string | null
  created_at: string
  updated_at: string | null
  last_login_at: string | null
}

export interface TokenDto {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserProfileUpdate {
  firstname?: string
  lastname?: string
  email?: string
  photo?: string | null
  timezone?: string
  base_currency?: string
  locale?: string
  theme?: string
  default_period?: 'day' | 'week' | 'month'
}

export interface UserExportDto {
  user: UserDto
  exported_at: string
  accounts: AccountDto[]
  categories: CategoryDto[]
  transactions: TransactionDto[]
  subscriptions: unknown[]
  currencies: CurrencyDto[]
}

/* -------------------------------- счета --------------------------------- */

export interface AccountDto {
  id: number
  user_id: string
  name: string
  type: AccountTypeValue
  currency_id: string
  balance: number
  is_archived: boolean
  is_excluded: boolean
  created_at: string
  updated_at: string | null
}

export interface AccountCreate {
  name: string
  type: AccountTypeValue
  currency_id: string
  balance?: number
  is_archived?: boolean
  is_excluded?: boolean
}

export interface AccountUpdate {
  name?: string
  type?: AccountTypeValue
  currency_id?: string
  balance?: number
  is_archived?: boolean
  is_excluded?: boolean
}

export interface AccountSummaryDto {
  account_id: number
  name: string
  currency_id: string
  balance: number
  is_archived: boolean
  is_excluded: boolean
  income: number
  expense: number
  net: number
  transactions_count: number
  start_date: string | null
  end_date: string | null
}

/** Общий баланс приходит единственным числом в базовой валюте пользователя. */
export interface BalanceOverviewDto {
  total: number
}

/* ------------------------------ категории ------------------------------- */

export interface CategoryDto {
  id: number
  user_id: string
  name: string
  type: CategoryTypeValue
  parent_id: number | null
  icon: string | null
  color: string | null
  created_at: string
  updated_at: string | null
}

export interface CategoryCreate {
  name: string
  type: CategoryTypeValue
  parent_id?: number | null
  icon?: string | null
  color?: string | null
}

export type CategoryUpdate = Partial<CategoryCreate>

export interface CategoryNodeDto {
  id: number
  name: string
  type: CategoryTypeValue
  parent_id: number | null
  icon: string | null
  color: string | null
  transactions_count: number
  children: CategoryNodeDto[]
}

export interface CategoryStatDto {
  category_id: number
  name: string
  type: CategoryTypeValue
  parent_id: number | null
  icon: string | null
  color: string | null
  transactions_count: number
  total: number
}

/* -------------------------------- записи -------------------------------- */

export interface TagInlineDto {
  id: number
  name: string
  color: string
}

export interface TransactionDto {
  id: number
  account_id: number
  category_id: number
  amount: number
  currency_id: string
  type: TransactionTypeValue
  date: string
  note: string | null
  is_subscription: boolean
  receipt_url: string | null
  is_excluded: boolean
  tag_ids: number[]
  tags: TagInlineDto[]
  created_at: string
}

export interface TransactionWithDetailsDto extends TransactionDto {
  account_name: string
  category_name: string
  category_color: string
  category_icon: string
  currency_symbol: string
}

export interface TransactionCreate {
  account_id: number
  category_id: number
  amount: number
  currency_id: string
  type: TransactionTypeValue
  date: string
  note?: string | null
  is_subscription?: boolean
  receipt_url?: string | null
  tag_ids?: number[]
}

export type TransactionUpdate = Partial<Omit<TransactionCreate, 'type'>> & { type?: TransactionTypeValue }

export interface TransactionSummaryDto {
  total: number
  transactions_count: number
  by_category: Array<{ category_id: number; name: string; total: number; transactions_count: number }>
  start_date: string | null
  end_date: string | null
}

export interface BulkDeleteResultDto {
  deleted: number
  missing: number[]
}

/** Фильтры списка записей: соответствуют query-параметрам `/finance/transactions/`. */
export interface TransactionFilters {
  account_ids?: number[]
  category_ids?: number[]
  currency_ids?: string[]
  types?: TransactionTypeValue[]
  tag_ids?: number[]
  q?: string
  amount_min?: number
  amount_max?: number
  start_date?: string
  end_date?: string
  sort?: 'date_desc' | 'date_asc' | 'amount_desc' | 'amount_asc'
  offset?: number
  limit?: number
}

/* -------------------------------- валюты -------------------------------- */

export interface CurrencyDto {
  code: string
  name: string
  symbol: string
  exchange_rate_to_base: number
  is_base?: boolean
}

export interface CurrencyRateDto {
  code: string
  name: string
  symbol: string
  rate: number
  is_base: boolean
  is_custom: boolean
}

/* ------------------------------- аналитика ------------------------------ */

export interface PeriodTotalsDto {
  start_date: string | null
  end_date: string | null
  income: number
  expense: number
  net: number
  transactions_count: number
}

export interface PeriodChangeDto {
  income: number | null
  expense: number | null
  net: number | null
}

export interface AnalyticsSummaryDto {
  start_date: string | null
  end_date: string | null
  income: number
  expense: number
  net: number
  transactions_count: number
  previous: PeriodTotalsDto | null
  change: PeriodChangeDto | null
}

export interface SeriesPointDto {
  date: string
  income?: number
  expense?: number
  net?: number
  value?: number
}

export interface TimeseriesDto {
  group_by: 'day' | 'week' | 'month' | string
  metric: 'cashflow' | 'balance' | string
  points: SeriesPointDto[]
}

export interface CategoryShareDto {
  category_id: number
  name: string
  type: CategoryTypeValue
  parent_id: number | null
  color: string | null
  icon: string | null
  total: number
  share: number
  transactions_count: number
}

export interface AccountShareDto {
  account_id: number
  name: string
  currency_id: string
  income: number
  expense: number
  net: number
  transactions_count: number
}

export interface MatrixRowDto {
  category_id: number | null
  name: string
  color: string | null
  icon: string | null
  values: number[]
  trends: number[]
}

export interface MatrixDto {
  months: string[]
  rows: MatrixRowDto[]
}

/* ------------------------ метки, шаблоны, правила ----------------------- */

export interface TagDto {
  id: number
  name: string
  color: string
  transactions_count: number
}

export interface TagCreate {
  name: string
  color?: string
}

export type TagUpdate = Partial<TagCreate>

export interface TemplateDto {
  id: number
  name: string
  type: TransactionTypeValue
  amount: number
  currency_id: string
  account_id: number
  category_id: number
  note: string | null
  icon: string
  usage_count: number
  tags: TagInlineDto[]
}

export interface TemplateCreate {
  name: string
  type: TransactionTypeValue
  amount: number
  currency_id: string
  account_id: number
  category_id: number
  note?: string | null
  icon?: string
  tag_ids?: number[]
}

export type TemplateUpdate = Partial<TemplateCreate>

export interface RuleDto {
  id: number
  name: string
  is_active: boolean
  priority: number
  field: RuleFieldValue
  operator: RuleOperatorValue
  value: string
  set_category_id: number | null
  add_tag_id: number | null
  exclude_from_statistics: boolean
  category_name: string | null
  tag_name: string | null
}

export interface RuleCreate {
  name: string
  is_active?: boolean
  priority?: number
  field: RuleFieldValue
  operator: RuleOperatorValue
  value: string
  set_category_id?: number | null
  add_tag_id?: number | null
  exclude_from_statistics?: boolean
}

export type RuleUpdate = Partial<RuleCreate>

export interface RuleApplyResultDto {
  matched_rules: number[]
  updated_transactions: number
  dry_run: boolean
}

/* -------------------------------- биллинг ------------------------------- */

export interface PlanDto {
  code: string
  name: string
  description: string | null
  price: number
  currency: string
  period: PlanPeriodValue
  features: string[]
  is_active: boolean
}

export interface ProviderInfoDto {
  code: string
  title: string
  methods: PaymentMethodKindValue[]
  is_configured: boolean
  is_default: boolean
  is_mock: boolean
}

export interface SubscriptionDto {
  id: number | null
  plan_code: string
  plan_name: string
  status: SubscriptionStatusValue
  started_at: string | null
  current_period_end: string | null
  cancel_at_period_end: boolean
  provider: string
}

/** Лимиты и премиум-возможности текущего тарифа. */
export interface EntitlementsDto {
  plan_code: string
  plan_name: string
  is_paid: boolean
  is_active: boolean
  max_accounts: number | null
  multi_currency: boolean
  advanced_analytics: boolean
  current_period_end: string | null
  reason: string | null
}

export interface CheckoutSessionDto {
  payment_id: number
  status: PaymentStatusValue
  provider: string
  provider_reference: string | null
  checkout_url: string | null
  requires_redirect: boolean
  subscription: SubscriptionDto | null
}

export interface PaymentMethodDto {
  id: number
  provider: string
  kind: PaymentMethodKindValue
  brand: string | null
  last4: string | null
  is_default: boolean
  created_at: string | null
}

export interface PaymentDto {
  id: number
  plan_code: string | null
  kind: PaymentKindValue
  amount: number
  currency: string
  status: PaymentStatusValue
  provider: string
  failure_reason: string | null
  created_at: string | null
}
