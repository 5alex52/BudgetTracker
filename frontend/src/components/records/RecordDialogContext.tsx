import { createContext, useContext, type ReactNode } from 'react'
import type { RecordItem } from '@/__shared__/types/models'

/**
 * Access to the record modal from anywhere in the app.
 *
 * The handler used to be passed as a prop only to Overview and Records, so the
 * "+ Record" button in the header was silent on other screens. The context closes
 * that gap: the header always knows what to open, and pages can invoke the create
 * or edit form from anywhere — without threading props through five layers.
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
    // Without a provider buttons must not crash: return safe stubs.
    return { openCreate: () => undefined, openEdit: () => undefined }
  }
  return context
}
