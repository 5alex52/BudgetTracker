import { NavLink } from 'react-router-dom'
import { ArrowLeftRight, LayoutGrid, LineChart, Receipt, Settings2, ShieldCheck, Wallet, type LucideIcon } from 'lucide-react'
import { cn } from '@/__shared__/utils/cn'
import { useI18n, type TranslationKey } from '@/i18n'
import { useAuthStore } from '@/store/auth'
import { GlassSurface } from '@/components/glass/GlassSurface'
import { Logo } from '@/components/brand/Logo'

export interface RailItem {
  to: string
  labelKey: TranslationKey
  icon: LucideIcon
}

export const RAIL_ITEMS: RailItem[] = [
  { to: '/', labelKey: 'nav.overview', icon: LayoutGrid },
  { to: '/accounts', labelKey: 'nav.accounts', icon: Wallet },
  { to: '/records', labelKey: 'nav.records', icon: ArrowLeftRight },
  { to: '/analytics', labelKey: 'nav.analytics', icon: LineChart },
  { to: '/subscriptions', labelKey: 'nav.subscriptions', icon: Receipt },
]

/**
 * Вертикальный рельс навигации на стекле.
 *
 * Сознательное отличие от референса: там горизонтальная полоса меню на всю
 * ширину экрана — самый узнаваемый элемент чужого продукта. Здесь навигация
 * живёт в плавающем рельсе слева, а верхняя панель отвечает только за контекст
 * страницы, поиск и действия.
 */
export function SideRail() {
  const { t } = useI18n()
  const user = useAuthStore((state) => state.user)

  const itemClass = (isActive: boolean) =>
    cn(
      'relative flex w-full flex-col items-center gap-1 rounded-md px-1 py-2 transition-colors duration-fast ease-out',
      isActive ? 'bg-surface-1/85 text-accent' : 'text-fg-secondary hover:bg-surface-1/40 hover:text-fg-primary',
    )

  return (
    <GlassSurface
      as="nav"
      level="md"
      glow
      aria-label={t('nav.menu')}
      className="fixed bottom-3 left-3 top-3 z-[var(--z-nav)] hidden w-[var(--rail-w)] flex-col items-center gap-1 rounded-xl p-1.5 md:flex"
    >
      <span className="my-1">
        <Logo size={36} />
      </span>

      {RAIL_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/'}
          className={({ isActive }) => itemClass(isActive)}
        >
          {({ isActive }) => (
            <>
              <span
                className={cn(
                  'absolute left-0 top-1/2 h-5 w-[2px] -translate-y-1/2 rounded-pill',
                  isActive ? 'bg-accent' : 'opacity-0',
                )}
                aria-hidden="true"
              />
              <item.icon className="size-5" aria-hidden="true" strokeWidth={1.75} />
              <span className="text-center text-[10px] leading-none">{t(item.labelKey)}</span>
            </>
          )}
        </NavLink>
      ))}

      <span className="my-1 h-px w-6 bg-stroke-subtle" aria-hidden="true" />

      {user?.is_superuser && (
        <NavLink to="/admin" className={({ isActive }) => itemClass(isActive)}>
          <ShieldCheck className="size-5" aria-hidden="true" strokeWidth={1.75} />
          <span className="text-center text-[10px] leading-none">{t('nav.admin')}</span>
        </NavLink>
      )}

      <NavLink to="/settings" className={({ isActive }) => itemClass(isActive)}>
        <Settings2 className="size-5" aria-hidden="true" strokeWidth={1.75} />
        <span className="text-center text-[10px] leading-none">{t('nav.settings')}</span>
      </NavLink>
    </GlassSurface>
  )
}
