import type { TranslationKey } from '@/i18n'

/**
 * Сервисы, которые нельзя оплатить из региона: блокировка на уровне самого
 * сервиса или рекламной сети. Ключ icon — из SERVICE_ICONS.
 */
export interface BlockedSubscription {
  icon: string
  name: string
  taglineKey: TranslationKey
  actionUrl: string
}

export const BLOCKED_SUBSCRIPTIONS: BlockedSubscription[] = [
  {
    icon: 'youtube',
    name: 'YouTube',
    taglineKey: 'subs.tagline.youtube',
    actionUrl: 'https://www.youtube.com',
  },
  {
    icon: 'netflix',
    name: 'Netflix',
    taglineKey: 'subs.tagline.netflix',
    actionUrl: 'https://www.netflix.com',
  },
]
