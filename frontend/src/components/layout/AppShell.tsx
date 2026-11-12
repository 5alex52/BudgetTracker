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
  /** Left panel (filters, settings navigation) — on glass */
  sidebar?: ReactNode
  /** Page header content (title + actions) */
  header?: ReactNode
  /** Page context in the top bar (breadcrumb) */
  context?: ReactNode
  onAddRecord?: () => void
}

/**
 * Shell for all working screens.
 *
 * Layers: blob background (fixed) → navbar/tab bar/sidebar (glass) → content (surface-1).
 * Rule: content never gets backdrop-filter, to avoid spending compositing
 * and "flattening" the stack effect.
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
            'mx-auto flex w-full max-w-container flex-1 items-start gap-[var(--sidebar-gap)] px-4 pb-24 pt-6 md:px-6 md:pb-10',
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
