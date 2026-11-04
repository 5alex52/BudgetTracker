import type { ReactNode } from 'react'
import { cn } from '@/__shared__/utils/cn'
import { useI18n } from '@/i18n'
import { GlassBackdrop } from '@/components/glass/GlassBackdrop'
import { TopBar } from './TopBar'
import { useRecordDialog } from '@/components/records/RecordDialogContext'
import { SideRail } from './SideRail'
import { TabBar } from './TabBar'

export interface AppShellProps {
  children: ReactNode
  /** Левая панель (фильтры, навигация настроек) — на стекле */
  sidebar?: ReactNode
  /** Содержимое шапки страницы (заголовок + действия) */
  header?: ReactNode
  /** Контекст страницы в верхней панели (хлебная крошка) */
  context?: ReactNode
  onAddRecord?: () => void
}

/**
 * Каркас всех рабочих экранов.
 *
 * Слои: фон-пятна (fixed) → навбар/таб-бар/сайдбар (стекло) → контент (surface-1).
 * Правило: контент никогда не получает backdrop-filter, чтобы не тратить композицию
 * и не «сплющивать» эффект стека.
 */
export function AppShell({ children, sidebar, header, context, onAddRecord }: AppShellProps) {
  const recordDialog = useRecordDialog()
  const addRecord = onAddRecord ?? recordDialog.openCreate
  const { t } = useI18n()

  return (
    <>
      <GlassBackdrop />
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[var(--z-toast)] focus:rounded-sm focus:bg-surface-1 focus:px-3 focus:py-2 focus:text-label"
      >
        {t('nav.skipToContent')}
      </a>

      <SideRail />

      <div className="relative z-[1] flex min-h-dvh flex-col md:pl-[calc(var(--rail-w)+12px)]">
        <TopBar onAddRecord={addRecord} context={context} />

        {header && (
          <div className="mx-auto w-full max-w-container px-4 pt-1 md:px-6">{header}</div>
        )}

        <div
          className={cn(
            'mx-auto flex w-full max-w-container flex-1 items-start gap-[var(--sidebar-gap)] px-4 pb-24 pt-4 md:px-6 md:pb-10',
          )}
        >
          {sidebar && (
            <aside className="hidden w-[var(--sidebar-w)] shrink-0 md:sticky md:top-[calc(var(--nav-h)+16px)] md:block">
              {sidebar}
            </aside>
          )}
          <main id="main" className="min-w-0 flex-1">
            {children}
          </main>
        </div>
      </div>

      <TabBar />
    </>
  )
}
