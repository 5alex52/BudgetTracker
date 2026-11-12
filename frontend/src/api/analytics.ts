/** Analytics: a separate backend app, prefix `/api/analytics`. */
import { request } from './client'
import type {
  AccountShareDto,
  AnalyticsSummaryDto,
  CategoryShareDto,
  MatrixDto,
  TimeseriesDto,
} from './types'

export interface Range {
  startDate?: string
  endDate?: string
}

export interface CategoryShareResponse {
  items: CategoryShareDto[]
  total: number
}

export interface AccountShareResponse {
  items: AccountShareDto[]
  total: number
}

export function getSummary(range: Range & { compare?: boolean } = {}): Promise<AnalyticsSummaryDto> {
  return request<AnalyticsSummaryDto>('/analytics/summary', {
    query: {
      start_date: range.startDate,
      end_date: range.endDate,
      compare: range.compare ?? true,
    },
  })
}

export function getTimeseries(
  params: Range & {
    metric?: 'cashflow' | 'balance'
    groupBy?: 'day' | 'week' | 'month'
  } = {},
): Promise<TimeseriesDto> {
  return request<TimeseriesDto>('/analytics/timeseries', {
    query: {
      metric: params.metric ?? 'cashflow',
      group_by: params.groupBy ?? 'day',
      start_date: params.startDate,
      end_date: params.endDate,
    },
  })
}

export function getByCategory(
  params: Range & {
    type?: 'income' | 'expense' | 'transfer'
    parentId?: number
    includeChildren?: boolean
    rollup?: boolean
  } = {},
): Promise<CategoryShareResponse> {
  return request<CategoryShareResponse>('/analytics/by-category', {
    query: {
      transaction_type: params.type ?? 'expense',
      parent_id: params.parentId,
      include_children: params.includeChildren ?? true,
      rollup: params.rollup ?? false,
      start_date: params.startDate,
      end_date: params.endDate,
    },
  })
}

export function getByAccount(range: Range = {}): Promise<AccountShareResponse> {
  return request<AccountShareResponse>('/analytics/by-account', {
    query: { start_date: range.startDate, end_date: range.endDate },
  })
}

export function getMatrix(
  params: {
    months?: number
    type?: 'income' | 'expense' | 'transfer'
    rollup?: boolean
    endDate?: string
  } = {},
): Promise<MatrixDto> {
  return request<MatrixDto>('/analytics/matrix', {
    query: {
      months: params.months ?? 6,
      transaction_type: params.type ?? 'expense',
      rollup: params.rollup ?? true,
      end_date: params.endDate,
    },
  })
}
