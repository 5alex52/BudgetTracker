import { ArrowLeftRight, Bitcoin, CalendarClock, LayoutGrid, LineChart, Receipt, Wallet, type LucideIcon } from 'lucide-react'
import type { TranslationKey } from '@/i18n'

export interface NavItem {
  to: string
  labelKey: TranslationKey
  icon: LucideIcon
}

/** Mobile tab bar items. */
export const NAV_ITEMS: NavItem[] = [
  { to: '/', labelKey: 'nav.overview', icon: LayoutGrid },
  { to: '/accounts', labelKey: 'nav.accounts', icon: Wallet },
  { to: '/records', labelKey: 'nav.records', icon: ArrowLeftRight },
  { to: '/analytics', labelKey: 'nav.analytics', icon: LineChart },
  { to: '/subscriptions', labelKey: 'nav.subscriptions', icon: Receipt },
  { to: '/auto-rules', labelKey: 'nav.autoRules', icon: CalendarClock },
  { to: '/crypto', labelKey: 'nav.crypto', icon: Bitcoin },
]
