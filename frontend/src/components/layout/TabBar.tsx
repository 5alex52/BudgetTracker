import { NavLink } from 'react-router-dom'
import { MoreHorizontal } from 'lucide-react'
import { cn } from '@/__shared__/utils/cn'
import { useI18n } from '@/i18n'
import { GlassSurface } from '@/components/glass/GlassSurface'
import { NAV_ITEMS } from './nav-items'
import { MoreSheet } from './MoreSheet'

const MOBILE_ITEMS = NAV_ITEMS

/**
 * Mobile navigation: glass tab bar with safe-area.
 * The fifth item opens the glass "More" Sheet (Investments, Imports, settings).
 */
export function TabBar() {
  const { t } = useI18n()

  return (
    <GlassSurface
      as="nav"
      level="md"
      variant="regular"
      className={cn(
        'scrollbar-none fixed inset-x-3 bottom-0 z-[var(--z-tabbar)] flex h-[var(--tabbar-h)] items-stretch gap-1 overflow-x-auto rounded-[22px] px-2 md:hidden',
      )}
      style={{ marginBottom: 'env(safe-area-inset-bottom)' }}
      aria-label={t('nav.menu')}
    >
      {MOBILE_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/'}
          className={({ isActive }) =>
            cn(
              'flex flex-1 min-w-[4rem] flex-col items-center justify-center gap-1 rounded-md text-[11px] leading-4 transition-colors duration-base ease-out',
              isActive
                ? 'text-accent'
                : 'text-fg-secondary hover:text-fg-primary',
            )
          }
        >
          <item.icon className="size-5" aria-hidden="true" />
          <span className="max-w-full truncate px-0.5">{t(item.labelKey)}</span>
        </NavLink>
      ))}

      <MoreSheet>
        <MoreHorizontal className="size-5" aria-hidden="true" />
        <span>{t('common.more')}</span>
      </MoreSheet>
    </GlassSurface>
  )
}
