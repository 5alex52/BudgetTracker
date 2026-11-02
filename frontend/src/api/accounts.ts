/** Счета: список, карточка, обороты, архивирование и исключение из статистики. */
import { request } from './client'
import type {
  AccountCreate,
  AccountDto,
  AccountSummaryDto,
  AccountUpdate,
  BalanceOverviewDto,
} from './types'

export function listAccounts(params?: { includeArchived?: boolean; includeExcluded?: boolean }): Promise<AccountDto[]> {
  return request<AccountDto[]>('/finance/accounts/', {
    query: {
      include_archived: params?.includeArchived ?? true,
      include_excluded: params?.includeExcluded ?? true,
      limit: 100,
    },
  })
}

export function getAccount(accountId: string | number): Promise<AccountDto> {
  return request<AccountDto>(`/finance/accounts/${accountId}`)
}

export function createAccount(payload: AccountCreate): Promise<AccountDto> {
  return request<AccountDto>('/finance/accounts/', { method: 'POST', body: payload })
}

export function updateAccount(accountId: string | number, payload: AccountUpdate): Promise<AccountDto> {
  return request<AccountDto>(`/finance/accounts/${accountId}`, { method: 'PATCH', body: payload })
}

export function deleteAccount(accountId: string | number): Promise<void> {
  return request<void>(`/finance/accounts/${accountId}`, { method: 'DELETE' })
}

export function setAccountArchived(accountId: string | number, isArchived: boolean): Promise<AccountDto> {
  return request<AccountDto>(`/finance/accounts/${accountId}/archive`, {
    method: 'POST',
    query: { is_archived: isArchived },
  })
}

export function setAccountExcluded(accountId: string | number, isExcluded: boolean): Promise<AccountDto> {
  return request<AccountDto>(`/finance/accounts/${accountId}/exclude`, {
    method: 'POST',
    query: { is_excluded: isExcluded },
  })
}

/** Обороты счёта за период: карточка «Баланс / Записи» в деталях. */
export function getAccountSummary(
  accountId: string | number,
  range?: { startDate?: string; endDate?: string },
): Promise<AccountSummaryDto> {
  return request<AccountSummaryDto>(`/finance/accounts/${accountId}/summary`, {
    query: { start_date: range?.startDate, end_date: range?.endDate },
  })
}

export function getTotalBalance(): Promise<BalanceOverviewDto> {
  return request<BalanceOverviewDto>('/finance/accounts/balance')
}
