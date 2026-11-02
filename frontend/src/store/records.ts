import { create } from 'zustand'
import { ApiError } from '@/api'
import * as transactionsApi from '@/api/transactions'
import { toRecordItem } from '@/api/mappers'
import type { TransactionCreate, TransactionFilters, TransactionUpdate, TransactionWithDetailsDto } from '@/api/types'
import type { RecordItem } from '@/__shared__/types/models'
import { useFinanceStore } from './finance'

/**
 * Записи: источник правды — backend.
 *
 * Раньше список жил в localStorage-сторе и фильтровался на клиенте. Теперь
 * фильтры уходят на сервер (он умеет и поиск, и диапазон сумм, и метки), а
 * стор хранит текущую страницу, итог и состояние загрузки.
 */
interface RecordsState {
  items: RecordItem[]
  total: number
  loading: boolean
  error: string | null
  filters: TransactionFilters

  /** Загрузить страницу с учётом фильтров; `append` — догрузка «показать ещё» */
  load: (filters?: TransactionFilters, options?: { append?: boolean }) => Promise<void>
  setFilters: (filters: TransactionFilters) => void
  reset: () => void

  create: (payload: TransactionCreate) => Promise<RecordItem>
  update: (id: string | number, payload: TransactionUpdate) => Promise<RecordItem>
  remove: (id: string | number) => Promise<void>
  bulkRemove: (ids: Array<string | number>) => Promise<number>
}

const PAGE_SIZE = 100

export const useRecordsStore = create<RecordsState>((set, get) => ({
  items: [],
  total: 0,
  loading: false,
  error: null,
  filters: { sort: 'date_desc', limit: PAGE_SIZE },

  load: async (filters, options) => {
    const merged = { ...get().filters, ...(filters ?? {}) }
    const append = options?.append ?? false
    set({ loading: true, error: null, filters: merged })
    try {
      const result = await transactionsApi.listTransactions({
        ...merged,
        offset: append ? get().items.length : 0,
        limit: merged.limit ?? PAGE_SIZE,
      })
      const lookup = { accounts: accountIndex() }
      const mapped = result.items.map((dto) => toRecordItem(dto, lookup))
      set({
        items: append ? [...get().items, ...mapped] : mapped,
        total: result.total,
        loading: false,
      })
    } catch (caught) {
      set({
        loading: false,
        error: caught instanceof ApiError ? caught.detail : String(caught),
      })
    }
  },

  setFilters: (filters) => set({ filters: { ...get().filters, ...filters } }),
  reset: () => set({ items: [], total: 0, filters: { sort: 'date_desc', limit: PAGE_SIZE } }),

  create: async (payload) => {
    const dto = await transactionsApi.createTransaction(payload)
    const item = await refreshItem(dto.id)
    await useFinanceStore.getState().reloadAccounts()
    // Свежая запись могла измениться правилами: берём данные с сервера
    set((state) => ({ items: [item, ...state.items], total: state.total + 1 }))
    return item
  },

  update: async (id, payload) => {
    const dto = await transactionsApi.updateTransaction(id, payload)
    const item = await refreshItem(dto.id)
    await useFinanceStore.getState().reloadAccounts()
    set((state) => ({
      items: state.items.map((row) => (row.id === item.id ? item : row)),
    }))
    return item
  },

  remove: async (id) => {
    await transactionsApi.deleteTransaction(id)
    await useFinanceStore.getState().reloadAccounts()
    set((state) => ({
      items: state.items.filter((row) => row.id !== String(id)),
      total: Math.max(0, state.total - 1),
    }))
  },

  bulkRemove: async (ids) => {
    const result = await transactionsApi.bulkDeleteTransactions(ids)
    await useFinanceStore.getState().reloadAccounts()
    const removed = new Set(ids.map(String))
    set((state) => ({
      items: state.items.filter((row) => !removed.has(row.id)),
      total: Math.max(0, state.total - result.deleted),
    }))
    return result.deleted
  },
}))

/** Индекс счетов по числовому id: по нему маппер берёт маркер цвета. */
function accountIndex() {
  const accounts = useFinanceStore.getState().accounts
  const byId = new Map<number, (typeof accounts)[number]>()
  accounts.forEach((account) => byId.set(Number(account.id), account))
  return byId
}

/** Детали записи для списка: сервер отдаёт их вместе с названиями счёта и категории. */
async function refreshItem(id: number): Promise<RecordItem> {
  const dto: TransactionWithDetailsDto = await transactionsApi.getTransaction(id)
  return toRecordItem(dto, { accounts: accountIndex() })
}
