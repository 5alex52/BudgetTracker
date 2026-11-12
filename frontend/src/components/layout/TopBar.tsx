import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { cn } from '@/__shared__/utils/cn'
import { useI18n } from '@/i18n'
import { GlassSurface } from '@/components/glass/GlassSurface'
import { Button } from '@/components/ui/button'
import { Wordmark } from '@/components/brand/Logo'
import { UserMenu } from './UserMenu'

/**
 * Floating top bar: not full-width but a "capsule" with insets,
 * in the spirit of macOS 26 panels. Brand on the left, then page context
 * (breadcrumb), on the right — record search, "+ Record" and the user menu.
 *
 * Difference from the reference: there the header is also the full-width main menu.
 * Here the menu moved to the left rail, and the bar handles context.
 */
export function TopBar({
  onAddRecord,
  context,
}: {
  onAddRecord?: () => void
  context?: ReactNode
}) {
  const { t } = useI18n()

  return (
    <GlassSurface
      as="header"
      level="md"
      glow
      className={cn(
        'sticky top-3 z-[var(--z-nav)] mx-3 mb-3 flex h-[var(--topbar-h)] items-center gap-3 rounded-xl px-3',
        'md:ml-[calc(var(--rail-w)+16px)] md:mr-4',
      )}
    >
      <Link to="/" aria-label={t('app.name')} className="rounded-sm focus-visible:outline-none md:hidden">
        <Wordmark size={24} />
      </Link>

      <div className="hidden min-w-0 items-center gap-2 md:flex">
        <Wordmark size={24} />
        {context && (
          <>
            <span className="text-fg-tertiary" aria-hidden="true">
              /
            </span>
            <span className="truncate text-label font-medium text-fg-primary">{context}</span>
          </>
        )}
      </div>

      <div className="ml-auto flex items-center gap-2">
        <Button size="sm" pill onClick={onAddRecord} className="gap-1.5">
          <Plus className="size-4" aria-hidden="true" />
          <span className="hidden sm:inline">{t('nav.addRecord')}</span>
        </Button>
        <UserMenu />
      </div>
    </GlassSurface>
  )
}
