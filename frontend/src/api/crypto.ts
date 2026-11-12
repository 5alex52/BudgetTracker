/** Crypto wallet tracker: addresses, balances, sync, overview in the base currency. */
import { request } from './client'
import type {
  CryptoAddressCreatePayload,
  CryptoBalancesUpdatePayload,
  CryptoGroupBy,
  CryptoOverviewDto,
  CryptoPeriod,
  CryptoTimeseriesDto,
  CryptoWalletBalancesDto,
  CryptoWalletCreatePayload,
  CryptoWalletDto,
  CryptoWalletListDto,
  CryptoWalletUpdatePayload,
} from './types'

export function listWallets(): Promise<CryptoWalletListDto> {
  return request<CryptoWalletListDto>('/crypto/wallets')
}

export function createWallet(payload: CryptoWalletCreatePayload): Promise<CryptoWalletDto> {
  return request<CryptoWalletDto>('/crypto/wallets', { method: 'POST', body: payload })
}

export function updateWallet(id: number, payload: CryptoWalletUpdatePayload): Promise<CryptoWalletDto> {
  return request<CryptoWalletDto>(`/crypto/wallets/${id}`, { method: 'PATCH', body: payload })
}

export function deleteWallet(id: number): Promise<void> {
  return request<void>(`/crypto/wallets/${id}`, { method: 'DELETE' })
}

export function addAddress(id: number, payload: CryptoAddressCreatePayload): Promise<void> {
  return request<void>(`/crypto/wallets/${id}/addresses`, { method: 'POST', body: payload })
}

export function removeAddress(id: number, addressId: number): Promise<void> {
  return request<void>(`/crypto/wallets/${id}/addresses/${addressId}`, { method: 'DELETE' })
}

export function syncWallet(id: number): Promise<void> {
  return request<void>(`/crypto/wallets/${id}/sync`, { method: 'POST' })
}

export function getBalances(id: number): Promise<CryptoWalletBalancesDto> {
  return request<CryptoWalletBalancesDto>(`/crypto/wallets/${id}/balances`)
}

export function updateBalances(id: number, payload: CryptoBalancesUpdatePayload): Promise<void> {
  return request<void>(`/crypto/wallets/${id}/balances`, { method: 'PUT', body: payload })
}

export function getOverview(period: CryptoPeriod): Promise<CryptoOverviewDto> {
  return request<CryptoOverviewDto>('/crypto/overview', { query: { period } })
}

export function getTimeseries(period: CryptoPeriod, groupBy: CryptoGroupBy): Promise<CryptoTimeseriesDto> {
  return request<CryptoTimeseriesDto>('/crypto/timeseries', { query: { period, group_by: groupBy } })
}

/** Asset codes for the manual balance editor. */
export function listAssets(): Promise<{ items: string[] }> {
  return request<{ items: string[] }>('/crypto/assets')
}
