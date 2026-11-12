/**
 * Backend request/response types — exactly what OpenAPI describes
 * (`/docs` of the backend service). Field names intentionally match the server:
 * mappers to UI models live separately (see `mappers.ts`), this is only the contract.
 */

export type TransactionTypeValue = 'income' | 'expense' | 'transfer'
export type CategoryTypeValue = 'income' | 'expense' | 'transfer'
export type AccountTypeValue = 'cash' | 'checking' | 'credit_card' | 'savings' | 'investment'

/* ------------------------------- profile --------------------------------- */

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
  telegram_id: number | null
  reminder_days_before: number | null
  created_at: string
  updated_at: string | null
  last_login_at: string | null
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
  reminder_days_before?: number
}

/** Telegram bot linking code: the user sends /start <code> to the bot */
export interface TelegramLinkDto {
  code: string
  bot_username: string | null
  deep_link: string | null
  chat_id: number | null
}

export interface PushSubscribeDto {
  endpoint: string
  keys: { p256dh: string; auth: string }
}

export interface PushPublicKeyDto {
  public_key: string
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

/* -------------------------------- accounts ------------------------------- */

export interface AccountDto {
  id: number
  user_id: string
  name: string
  type: AccountTypeValue
  currency_id: string
  balance: number
  is_archived: boolean
  is_excluded: boolean
  /** Crypto wallet flag: the account is managed from the Crypto page */
  crypto_kind?: string | null
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

/** Account balance at period end: in the account currency and in the base currency. */
export interface BalanceOverviewAccountDto {
  account_id: number
  name: string
  currency_id: string
  balance: number
  balance_base: number
  is_archived: boolean
  is_excluded: boolean
}

/** The total balance arrives already converted to the user's base currency. */
export interface BalanceOverviewDto {
  total: number
  accounts: BalanceOverviewAccountDto[]
}

/* ------------------------------ categories ------------------------------- */

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

/* -------------------------------- records -------------------------------- */

export interface TagInlineDto {
  id: number
  name: string
  color: string
}

export interface TransactionDto {
  id: number
  account_id: number
  category_id: number
  /** Transfer destination account (type=transfer only) */
  transfer_account_id: number | null
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
  /** Name of the transfer destination account */
  transfer_account_name: string | null
}

export interface TransactionCreate {
  account_id: number
  /** A transfer has no category — the server substitutes a system one */
  category_id?: number
  transfer_account_id?: number | null
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

/** Record list filters: match the query parameters of `/finance/transactions/`. */
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

/* -------------------------------- currencies ----------------------------- */

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

/* ------------------------------- analytics ------------------------------- */

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
  parent_id: number | null
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

/* --------------------------- tags, templates ----------------------------- */

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

/* ------------------------------- admin ----------------------------------- */

export interface AdminUserDto {
  id: string
  fullname: string
  email: string
  is_active: boolean
  is_verified: boolean
  is_superuser: boolean
  created_at: string
  last_login_at: string | null
}

export interface AdminUserPageDto {
  items: AdminUserDto[]
  total: number
  offset: number
  limit: number
}

export interface AdminUserUpdate {
  firstname?: string
  lastname?: string
  email?: string
  is_active?: boolean
  is_verified?: boolean
}

/* ---------------------------- service subscriptions ----------------------- */

export interface ServiceSubChargeDto {
  id: number
  date: string
  amount: number
  currency_id: string
}

export interface ServiceSubDto {
  id: number
  name: string
  icon: string | null
  price: number
  currency_id: string
  started_at: string
  price_base: number
  account_id: number | null
  next_payment_date: string | null
  frequency: string
  rule_active: boolean | null
  charges: ServiceSubChargeDto[]
  created_at: string
  updated_at: string | null
}

export interface ServiceSubMonthTotalDto {
  month: string
  total: number
}

export interface ServiceSubListDto {
  items: ServiceSubDto[]
  total_base: number
  base_currency: string
}

/** Charge frequency offered by the UI (the server also knows daily/weekly). */
export type ServiceSubFrequency = 'monthly' | 'quarterly' | 'yearly'

export interface ServiceSubCreatePayload {
  name: string
  icon?: string | null
  price: number
  currency_id: string
  started_at: string
  account_id?: number | null
  frequency?: ServiceSubFrequency
}

/* ------------------------------- Crypto wallets -------------------------------- */

export type CryptoPeriod = '7d' | '30d' | '90d' | '1y' | 'all'
export type CryptoGroupBy = 'total' | 'asset' | 'wallet'
export type CryptoChain = 'evm' | 'btc' | 'ton' | 'tron' | 'solana' | 'avalanche'
export type CryptoWalletKind = 'trust' | 'telegram' | 'manual'
export type CryptoSyncStatus = 'ok' | 'error' | 'partial'

export interface CryptoAddressDto {
  id: number
  chain: CryptoChain
  address: string
  is_active: boolean
}

export interface CryptoHoldingDto {
  asset_code: string
  amount: string
}

export interface CryptoWalletDto {
  id: number
  name: string
  kind: CryptoWalletKind
  addresses: CryptoAddressDto[]
  holdings: CryptoHoldingDto[]
  total_usd: string
  total_base: string
  base_currency: string
  last_sync_at: string | null
  last_sync_status: CryptoSyncStatus | null
  created_at: string
  updated_at: string | null
}

export interface CryptoWalletListDto {
  items: CryptoWalletDto[]
}

export interface CryptoWalletCreatePayload {
  name: string
  kind: CryptoWalletKind
  addresses?: Array<{ chain: CryptoChain; address: string }>
  holdings?: CryptoHoldingDto[]
}

export interface CryptoWalletUpdatePayload {
  name?: string
}

export interface CryptoAddressCreatePayload {
  chain: CryptoChain
  address: string
}

export interface CryptoBalancesUpdatePayload {
  holdings: CryptoHoldingDto[]
}

export interface CryptoWalletBalancesDto {
  items: Array<{
    asset_code: string
    amount: string
    price_usd: string
    value_usd: string
    value_base: string
  }>
  base_currency: string
}

export interface CryptoOverviewDto {
  total_now_base: string
  base_currency: string
  change_absolute: string
  change_percent: string
  by_asset: Array<{
    asset_code: string
    amount: string
    price_usd: string
    value_base: string
    change_percent: string
  }>
  by_wallet: Array<{
    wallet_id: number
    name: string
    value_base: string
    change_percent: string
  }>
}

export interface CryptoTimeseriesDto {
  points: Array<{
    day: string
    total_base: string
    by_asset: Record<string, string>
    by_wallet: Record<string, string>
  }>
}

export interface ServiceSubUpdatePayload {
  name?: string
  icon?: string | null
  price?: number
  currency_id?: string
  started_at?: string
  account_id?: number | null
  rule_active?: boolean
  frequency?: ServiceSubFrequency
}
