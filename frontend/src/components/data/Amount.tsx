import type { Currency } from '@/__shared__/mock/finance'
import { useI18n } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'

const SUFFIX: Record<Currency, string> = {
  BYN: 'BYN',
  RUB: '₽',
  USD: '$',
  EUR: '€',
}

export interface AmountProps {
  value: number
  currency?: Currency
  /** Скрыть копейки (настройка «Формат числа») */
  hideDecimals?: boolean
  /** Показывать знак + для положительных */
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
 * Сумма с валютой. Дробная часть набирается Medeo Mono: цифры не «пляшут»
 * при обновлении и выравниваются в таблицах.
 */
export function Amount({
  value,
  currency = 'BYN',
  hideDecimals = false,
  signed = false,
  tone = 'auto',
  size = 'md',
  className,
}: AmountProps) {
  const { number } = useI18n()
  const abs = Math.abs(value)
  const formatted = number(abs, {
    minimumFractionDigits: hideDecimals ? 0 : 2,
    maximumFractionDigits: hideDecimals ? 0 : 2,
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
      aria-label={`${sign}${formatted} ${SUFFIX[currency]}`}
    >
      <span aria-hidden="true">
        {sign}
        {formatted}
      </span>
      <span className="text-[0.78em] font-normal text-fg-tertiary" aria-hidden="true">
        {SUFFIX[currency]}
      </span>
    </span>
  )
}

/** Значок изменения: стрелка + проценты. Цвет дублируется направлением стрелки. */
export function TrendBadge({
  value,
  className,
}: {
  value: number
  className?: string
}) {
  const { number } = useI18n()
  const tone = value > 0 ? 'positive' : value < 0 ? 'negative' : 'neutral'
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
