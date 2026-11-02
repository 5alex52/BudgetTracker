import { create } from 'zustand'
import { accounts as seed, type Account, type AccountKind, type Currency } from '@/__shared__/mock/finance'

/**
 * Локальное состояние счетов: список, создание, правка, удаление.
 * До API это единственный источник правды для «Счетов», «Обзора» и деталей счёта.
 */
interface AccountsState {
  items: Account[]
  upsert: (account: Account) => void
  remove: (id: string) => void
  nextId: (name: string) => string
}

let counter = 0

export const useAccountsStore = create<AccountsState>((set, get) => ({
  items: seed,
  upsert: (account) =>
    set((state) => {
      const exists = state.items.some((row) => row.id === account.id)
      return { items: exists ? state.items.map((row) => (row.id === account.id ? account : row)) : [...state.items, account] }
    }),
  remove: (id) => set((state) => ({ items: state.items.filter((row) => row.id !== id) })),
  nextId: (name) => {
    counter += 1
    const slug = name
      .toLowerCase()
      .replace(/[^a-zа-я0-9]+/gi, '-')
      .replace(/^-|-$/g, '')
      .slice(0, 24)
    return `${slug || 'account'}-${counter}-${get().items.length}`
  },
}))

export const ACCOUNT_KINDS: AccountKind[] = ['checking', 'savings', 'cash', 'general']
export const ACCOUNT_CURRENCIES: Currency[] = ['BYN', 'RUB', 'USD', 'EUR']
export const ACCOUNT_TINTS = ['#d94b4b', '#e06fa0', '#e08a3c', '#3aa76d', '#2ba7d6', '#5b8fd6', '#8b6fd6', '#c26bd6']

export const KIND_LABEL_KEY = {
  checking: 'accounts.type.checking',
  savings: 'accounts.type.savings',
  cash: 'accounts.type.cash',
  general: 'accounts.type.general',
} as const

/** Пустой счёт для формы создания. */
export const emptyAccount = (): Account => ({
  id: '',
  name: '',
  kind: 'checking',
  balance: 0,
  currency: 'BYN',
  tint: ACCOUNT_TINTS[4],
})
