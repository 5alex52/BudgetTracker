import { createContext, useContext, type ReactNode } from 'react'
import type { RecordItem } from '@/__shared__/types/models'

/**
 * Доступ к модалу записи из любого места приложения.
 *
 * Раньше обработчик передавался пропсом только на «Обзор» и «Записи», поэтому
 * кнопка «+ Запись» в шапке на остальных экранах молчала. Контекст закрывает
 * эту дыру: шапка всегда знает, что открыть, а страницы могут вызвать форму
 * создания или правки откуда угодно — без протягивания пропсов через пять слоёв.
 */
interface RecordDialogContextValue {
  openCreate: () => void
  openEdit: (record: RecordItem) => void
}

const RecordDialogContext = createContext<RecordDialogContextValue | null>(null)

export function RecordDialogProvider({
  value,
  children,
}: {
  value: RecordDialogContextValue
  children: ReactNode
}) {
  return <RecordDialogContext.Provider value={value}>{children}</RecordDialogContext.Provider>
}

export function useRecordDialog(): RecordDialogContextValue {
  const context = useContext(RecordDialogContext)
  if (!context) {
    // Без провайдера кнопки не должны падать: возвращаем безопасные заглушки.
    return { openCreate: () => undefined, openEdit: () => undefined }
  }
  return context
}
