import { ArrowLeftRight, LayoutGrid, LineChart, Wallet, type LucideIcon } from 'lucide-react'
import type { TranslationKey } from '@/i18n'

export interface NavItem {
  to: string
  labelKey: TranslationKey
  icon: LucideIcon
}

/** Пункты мобильного таб-бара. */
export const NAV_ITEMS: NavItem[] = [
  { to: '/', labelKey: 'nav.overview', icon: LayoutGrid },
  { to: '/accounts', labelKey: 'nav.accounts', icon: Wallet },
  { to: '/records', labelKey: 'nav.records', icon: ArrowLeftRight },
  { to: '/analytics', labelKey: 'nav.analytics', icon: LineChart },
]
