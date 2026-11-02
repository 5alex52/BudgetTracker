import { create } from 'zustand'
import { records as seed, type RecordItem } from '@/__shared__/mock/finance'

/**
 * Локальное состояние записей.
 *
 * До подключения API это единственное место, где живут записи: экран «Записи»,
 * детали счёта и модал добавления/редактирования читают и пишут сюда, поэтому
 * создание, правка и удаление сразу видны во всём интерфейсе и переживают
 * переходы между страницами.
 */
interface RecordsState {
  items: RecordItem[]
  upsert: (item: RecordItem) => void
  remove: (id: string) => void
  nextId: () => string
}

let counter = 0

export const useRecordsStore = create<RecordsState>((set, get) => ({
  items: seed,
  upsert: (item) =>
    set((state) => {
      const exists = state.items.some((row) => row.id === item.id)
      return { items: exists ? state.items.map((row) => (row.id === item.id ? item : row)) : [item, ...state.items] }
    }),
  remove: (id) => set((state) => ({ items: state.items.filter((row) => row.id !== id) })),
  nextId: () => {
    counter += 1
    return `rec-new-${Date.now()}-${counter}-${get().items.length}`
  },
}))

/** Форма записи для модала: суммы — по модулю, тип и валюта — отдельно. */
export function toFormValues(item: RecordItem) {
  return {
    type: item.type,
    amount: String(Math.abs(item.amount)).replace('.', ','),
    account: item.account,
    category: item.category,
    note: item.note ?? '',
    date: item.date,
    time: item.time,
    currency: item.currency,
  }
}
