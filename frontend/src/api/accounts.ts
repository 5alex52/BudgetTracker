/** Accounts: list, card, turnover, archiving and exclusion from statistics. */
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

/** Account turnover for a period: the "Balance / Records" card in details. */
export function getAccountSummary(
  accountId: string | number,
  range?: { startDate?: string; endDate?: string },
): Promise<AccountSummaryDto> {
  return request<AccountSummaryDto>(`/finance/accounts/${accountId}/summary`, {
    query: { start_date: range?.startDate, end_date: range?.endDate },
  })
}

/** Balance across all accounts in the base currency; with a period — balance at period end. */
export function getTotalBalance(range?: { startDate?: string; endDate?: string }): Promise<BalanceOverviewDto> {
  return request<BalanceOverviewDto>('/finance/accounts/balance', {
    query: { start_date: range?.startDate, end_date: range?.endDate },
  })
}
