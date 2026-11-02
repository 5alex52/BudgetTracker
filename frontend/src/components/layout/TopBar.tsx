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
 * Плавающая верхняя панель: не на всю ширину, а «капсулой» с отступами,
 * в духе панелей macOS 26. Слева — бренд, затем контекст страницы (хлебная
 * крошка), справа — поиск по записям, «+ Запись» и меню пользователя.
 *
 * Отличие от референса: там шапка — это ещё и главное меню на всю ширину.
 * Здесь меню вынесено в левый рельс, а панель отвечает за контекст.
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
        'lg:ml-[calc(var(--rail-w)+16px)] lg:mr-4',
      )}
    >
      <Link to="/" aria-label={t('app.name')} className="rounded-sm focus-visible:outline-none lg:hidden">
        <Wordmark size={24} />
      </Link>

      <div className="hidden min-w-0 items-center gap-2 lg:flex">
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
