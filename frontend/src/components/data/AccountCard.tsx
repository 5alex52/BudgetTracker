import { memo } from 'react'
import { Bitcoin, EyeOff } from 'lucide-react'
import type { Account } from '@/__shared__/types/models'
import { cn } from '@/__shared__/utils/cn'
import { useI18n } from '@/i18n'
import { Amount } from './Amount'

/**
 * Плитка счёта на дашборде. В референсе это цветные карточки 268×50.
 * Здесь цвет остаётся маркером счёта (узнаваемость), но приглушён: насыщенная
 * заливка спорила бы со стеклом и мешала контрасту сумм.
 */
function AccountCardImpl({
  account,
  className,
  onOpen,
}: {
  account: Account
  className?: string
  /** Открыть детали счёта: карточка становится ссылкой на /accounts/:id */
  onOpen?: () => void
}) {
  const { t } = useI18n()
  return (
    <button
      type="button"
      onClick={onOpen}
      className={cn(
        'group relative flex h-[50px] w-full flex-col justify-center overflow-hidden rounded-md border border-stroke-subtle px-3 text-left',
        'bg-surface-1 transition-[transform,background-color,border-color] duration-fast ease-out',
        'hover:-translate-y-px hover:border-stroke-strong active:translate-y-0',
        'motion-reduce:hover:translate-y-0',
        className,
      )}
      aria-label={`${account.name}: ${account.balance} ${account.currency}`}
    >
      <span
        className="absolute inset-y-0 left-0 w-[3px]"
        style={{ backgroundColor: account.tint }}
        aria-hidden="true"
      />
      <span className="flex items-center gap-1.5">
        <span className="truncate text-caption text-fg-secondary">{account.name}</span>
        {account.crypto && (
          <Bitcoin className="size-3 shrink-0 text-fg-tertiary" aria-label={t('accounts.cryptoBadge')} />
        )}
        {account.excluded && (
          <EyeOff className="size-3 shrink-0 text-fg-tertiary" aria-label={t('accounts.excluded')} />
        )}
      </span>
      <Amount value={account.balance} currency={account.currency} tone="neutral" size="sm" className="mt-0.5" />
    </button>
  )
}

/** Карточка счёта: перерисовывается только при смене данных счёта. */
export const AccountCard = memo(AccountCardImpl)
