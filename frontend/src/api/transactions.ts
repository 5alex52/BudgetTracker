/** Записи: список с фильтрами и пагинацией, CRUD, массовое удаление, выгрузка. */
import { API_BASE, request, requestWithHeaders } from './client'
import type {
  BulkDeleteResultDto,
  TransactionCreate,
  TransactionDto,
  TransactionFilters,
  TransactionSummaryDto,
  TransactionWithDetailsDto,
  TransactionUpdate,
} from './types'

export interface TransactionListResult {
  items: TransactionWithDetailsDto[]
  /** Всего записей по фильтру — из заголовка `X-Total-Count` */
  total: number
}

export async function listTransactions(
  filters: TransactionFilters = {},
): Promise<TransactionListResult> {
  const { data, headers } = await requestWithHeaders<TransactionWithDetailsDto[]>(
    '/finance/transactions/',
    {
      query: {
        account_ids: filters.account_ids,
        category_ids: filters.category_ids,
        currency_ids: filters.currency_ids,
        types: filters.types,
        tag_ids: filters.tag_ids,
        q: filters.q,
        amount_min: filters.amount_min,
        amount_max: filters.amount_max,
        start_date: filters.start_date,
        end_date: filters.end_date,
        sort: filters.sort,
        with_total: true,
        offset: filters.offset ?? 0,
        limit: filters.limit ?? 100,
      },
    },
  )
  const total = Number(headers.get('X-Total-Count') ?? data.length)
  return { items: data, total: Number.isFinite(total) ? total : data.length }
}

export function getTransaction(transactionId: string | number): Promise<TransactionWithDetailsDto> {
  return request<TransactionWithDetailsDto>(`/finance/transactions/${transactionId}`)
}

export function createTransaction(payload: TransactionCreate): Promise<TransactionDto> {
  return request<TransactionDto>('/finance/transactions/', { method: 'POST', body: payload })
}

export function updateTransaction(
  transactionId: string | number,
  payload: TransactionUpdate,
): Promise<TransactionDto> {
  return request<TransactionDto>(`/finance/transactions/${transactionId}`, {
    method: 'PATCH',
    body: payload,
  })
}

export function deleteTransaction(transactionId: string | number): Promise<void> {
  return request<void>(`/finance/transactions/${transactionId}`, { method: 'DELETE' })
}

export function bulkDeleteTransactions(ids: Array<string | number>): Promise<BulkDeleteResultDto> {
  return request<BulkDeleteResultDto>('/finance/transactions/bulk-delete', {
    method: 'POST',
    body: { ids: ids.map((id) => Number(id)) },
  })
}

export function getTransactionSummary(params?: {
  type?: 'income' | 'expense' | 'transfer'
  startDate?: string
  endDate?: string
}): Promise<TransactionSummaryDto> {
  return request<TransactionSummaryDto>('/finance/transactions/summary', {
    query: { transaction_type: params?.type, start_date: params?.startDate, end_date: params?.endDate },
  })
}

/** Ссылка на серверную выгрузку: браузер скачает файл с учётной cookie. */
export function exportTransactionsUrl(
  filters: TransactionFilters & { format?: 'csv' | 'json' },
): string {
  const params = new URLSearchParams()
  if (filters.format) params.set('format', filters.format)
  filters.account_ids?.forEach((id) => params.append('account_ids', String(id)))
  filters.category_ids?.forEach((id) => params.append('category_ids', String(id)))
  filters.currency_ids?.forEach((code) => params.append('currency_ids', code))
  filters.types?.forEach((type) => params.append('types', type))
  filters.tag_ids?.forEach((id) => params.append('tag_ids', String(id)))
  if (filters.q) params.set('q', filters.q)
  if (filters.amount_min !== undefined) params.set('amount_min', String(filters.amount_min))
  if (filters.amount_max !== undefined) params.set('amount_max', String(filters.amount_max))
  if (filters.start_date) params.set('start_date', filters.start_date)
  if (filters.end_date) params.set('end_date', filters.end_date)
  const query = params.toString()
  return `${API_BASE}/finance/transactions/export${query ? `?${query}` : ''}`
}
