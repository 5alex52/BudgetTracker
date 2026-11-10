import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { CircleHelp, Coins, Shield, SlidersHorizontal, Tag, Tags, User } from 'lucide-react'
import { cn } from '@/__shared__/utils/cn'
import { useI18n, type TranslationKey } from '@/i18n'
import { AppShell } from '@/components/layout/AppShell'

/** Бот поддержки: адрес задаётся при сборке, чтобы не пересобирать код. */
const TELEGRAM_SUPPORT_URL =
  (import.meta.env.VITE_TELEGRAM_SUPPORT_URL as string | undefined) ?? 'https://t.me/budgettracker_bot'

const GROUPS: Array<{
  id: string
  title: TranslationKey
  items: Array<{ to: string; labelKey: TranslationKey; icon: typeof Coins; external?: string }>
}> = [
  {
    id: 'wallet',
    title: 'settings.group.wallet',
    items: [
      { to: '/settings/currencies', labelKey: 'settings.currencies', icon: Coins },
      { to: '/settings/categories', labelKey: 'settings.categories', icon: Tag },
      { to: '/settings/templates', labelKey: 'settings.templates', icon: SlidersHorizontal },
      { to: '/settings/tags', labelKey: 'settings.tags', icon: Tags },
      { to: '/settings/rules', labelKey: 'settings.rules', icon: SlidersHorizontal },
    ],
  },
  {
    id: 'general',
    title: 'settings.group.general',
    items: [
      { to: '/settings', labelKey: 'settings.general', icon: User },
      { to: '/settings/privacy', labelKey: 'settings.privacy', icon: Shield },
      {
        to: '/settings/help',
        labelKey: 'settings.help',
        icon: CircleHelp,
        external: TELEGRAM_SUPPORT_URL,
      },
    ],
  },
]

/**
 * Общий каркас раздела настроек: слева навигация по подразделам, справа —
 * содержимое. Одинаковая структура для всех страниц настроек, чтобы переходы
 * не «прыгали», а навигация была на одном месте.
 */
export function SettingsLayout({
  title,
  subtitle,
  actions,
  children,
}: {
  title: string
  subtitle?: string
  actions?: ReactNode
  children: ReactNode
}) {
  const { t } = useI18n()

  return (
    <AppShell
      context={t('settings.title')}
      sidebar={
        <nav aria-label={t('settings.title')} className="content-card p-3">
          {GROUPS.map((group) => (
            <div key={group.id} className="mb-3 last:mb-0">
              <p className="px-2 py-1 text-overline uppercase tracking-wide text-fg-tertiary">{t(group.title)}</p>
              <ul>
                {group.items.map((item) => (
                  <li key={item.to}>
                    {item.external ? (
                      <a
                        href={item.external}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-2 rounded-sm px-2 py-1.5 text-label text-fg-secondary transition-colors duration-fast hover:bg-surface-2 hover:text-fg-primary"
                      >
                        <item.icon className="size-4 shrink-0" aria-hidden="true" strokeWidth={1.75} />
                        <span className="truncate">{t(item.labelKey)}</span>
                      </a>
                    ) : (
                      <NavLink
                        to={item.to}
                        end={item.to === '/settings'}
                        className={({ isActive }) =>
                          cn(
                            'flex items-center gap-2 rounded-sm px-2 py-1.5 text-label transition-colors duration-fast',
                            isActive
                              ? 'bg-accent/12 font-medium text-accent'
                              : 'text-fg-secondary hover:bg-surface-2 hover:text-fg-primary',
                          )
                        }
                      >
                        <item.icon className="size-4 shrink-0" aria-hidden="true" strokeWidth={1.75} />
                        <span className="truncate">{t(item.labelKey)}</span>
                      </NavLink>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>
      }
      header={
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-title font-semibold tracking-snug text-fg-primary">{title}</h1>
            {subtitle && <p className="mt-1 text-label text-fg-secondary">{subtitle}</p>}
          </div>
          {actions}
        </div>
      }
    >
      {/* На телефоне боковая навигация настроек скрыта — показываем её чипами */}
      <nav aria-label={t('settings.title')} className="-mx-1 mb-4 flex gap-1 overflow-x-auto px-1 pb-1 md:hidden">
        {GROUPS.flatMap((group) => group.items).map((item) => {
          const chipClass =
            'flex shrink-0 items-center gap-1.5 rounded-pill border border-stroke-subtle px-3 py-1.5 text-caption text-fg-secondary transition-colors duration-fast hover:bg-surface-2 hover:text-fg-primary'
          const content = (
            <>
              <item.icon className="size-3.5" aria-hidden="true" strokeWidth={1.75} />
              <span className="whitespace-nowrap">{t(item.labelKey)}</span>
            </>
          )
          return item.external ? (
            <a key={item.to} href={item.external} target="_blank" rel="noreferrer" className={chipClass}>
              {content}
            </a>
          ) : (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/settings'}
              className={({ isActive }) =>
                cn(
                  chipClass,
                  isActive && 'border-accent/30 bg-accent/12 font-medium text-accent',
                )
              }
            >
              {content}
            </NavLink>
          )
        })}
      </nav>
      {children}
    </AppShell>
  )
}
