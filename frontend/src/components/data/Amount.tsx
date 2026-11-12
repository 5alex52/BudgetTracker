import { memo } from 'react'
import type { Currency } from '@/__shared__/types/models'
import { useI18n } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'

/** Currency symbols; for other codes we show the code itself. */
const SUFFIX: Record<string, string> = {
  BYN: 'BYN',
  RUB: '₽',
  USD: '$',
  EUR: '€',
}

const symbolOf = (currency: Currency) => SUFFIX[currency] ?? currency

export interface AmountProps {
  value: number
  currency?: Currency
  /** Show a + sign for positive values */
  signed?: boolean
  tone?: 'auto' | 'neutral' | 'positive' | 'negative'
  size?: 'xs' | 'sm' | 'md' | 'lg'
  className?: string
}

const SIZE: Record<NonNullable<AmountProps['size']>, string> = {
  xs: 'text-caption',
  sm: 'text-metric-sm',
  md: 'text-metric',
  lg: 'text-metric-xl',
}

/**
 * Amount with currency. The fractional part is set in Medeo Mono: digits don't jitter
 * on updates and line up in tables.
 */
function AmountImpl({
  value,
  currency = 'BYN',
  signed = false,
  tone = 'auto',
  size = 'md',
  className,
}: AmountProps) {
  const { number } = useI18n()
  const abs = Math.abs(value)
  const formatted = number(abs, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
  const resolvedTone =
    tone === 'auto' ? (value > 0 ? 'positive' : value < 0 ? 'negative' : 'neutral') : tone
  const sign = value < 0 ? '−' : signed && value > 0 ? '+' : ''

  return (
    <span
      className={cn(
        'num inline-flex items-baseline gap-1 whitespace-nowrap tabular-nums',
        SIZE[size],
        resolvedTone === 'positive' && 'text-positive',
        resolvedTone === 'negative' && 'text-negative',
        resolvedTone === 'neutral' && 'text-fg-primary',
        className,
      )}
      aria-label={`${sign}${formatted} ${symbolOf(currency)}`}
    >
      <span aria-hidden="true">
        {sign}
        {formatted}
      </span>
      <span className="text-[0.78em] font-normal text-fg-tertiary" aria-hidden="true">
        {symbolOf(currency)}
      </span>
    </span>
  )
}

/** Change badge: arrow + percent. Color is duplicated by the arrow direction. */
export function TrendBadge({
  value,
  invert = false,
  className,
}: {
  value: number
  /** Expenses: growing spending is bad, so the color is inverted, the arrow is not. */
  invert?: boolean
  className?: string
}) {
  const { number } = useI18n()
  const tone = (invert ? -value : value) > 0 ? 'positive' : value !== 0 ? 'negative' : 'neutral'
  const arrow = value > 0 ? '↗' : value < 0 ? '↘' : '→'

  return (
    <span
      className={cn(
        'tnum inline-flex items-center gap-1 text-caption tabular-nums',
        tone === 'positive' && 'text-positive',
        tone === 'negative' && 'text-negative',
        tone === 'neutral' && 'text-fg-tertiary',
        className,
      )}
    >
      <span aria-hidden="true">{arrow}</span>
      <span>
        {value > 0 ? '' : ''}
        {number(Math.abs(value))}%
      </span>
    </span>
  )
}

export function CurrencyTag({ currency, className }: { currency: Currency; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex h-5 items-center rounded-xs bg-surface-2 px-1.5 text-[11px] font-medium uppercase tracking-wide text-fg-secondary',
        className,
      )}
    >
      {currency}
    </span>
  )
}

/** Amount: memo so lists don't re-run formatting for nothing. */
export const Amount = memo(AmountImpl)
