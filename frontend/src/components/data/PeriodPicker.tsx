import { useEffect, useState } from 'react'
import type { DateRange } from 'react-day-picker'
import { DayPicker } from 'react-day-picker'
import { ru, enUS } from 'date-fns/locale'
import { CalendarRange, ChevronLeft, ChevronRight } from 'lucide-react'
import { useI18n } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/overlays'
import 'react-day-picker/style.css'

/** Whether the calendar is single-column: two months don't fit on narrow screens. */
function useCompactLayout() {
  const [compact, setCompact] = useState(
    () => typeof window !== 'undefined' && window.matchMedia('(max-width: 639px)').matches,
  )
  useEffect(() => {
    const query = window.matchMedia('(max-width: 639px)')
    const onChange = (event: MediaQueryListEvent) => setCompact(event.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])
  return compact
}

/**
 * Period picker: month arrows + a date-range calendar.
 *
 * The calendar uses `react-day-picker` — the standard date-picking library
 * in the shadcn/Radix ecosystem: range mode, locales for us and keyboard
 * accessibility, without a 400-line homegrown wheel.
 * The text above the calendar shows the current selection just like the reference.
 */
export interface PeriodPickerProps {
  /** Default period label: "October 2025" / "October 1–31, 2025" */
  label: string
  onPrev?: () => void
  onNext?: () => void
  range?: DateRange
  onRangeChange?: (range: DateRange | undefined) => void
  /** Month the calendar opens on (current by default) */
  defaultMonth?: Date
  className?: string
}

const PRESETS = ['today', 'thisMonth', 'lastMonth', 'last3Months', 'thisYear'] as const

export function PeriodPicker({
  label,
  onPrev,
  onNext,
  range,
  onRangeChange,
  defaultMonth,
  className,
}: PeriodPickerProps) {
  const { t, locale } = useI18n()
  const compact = useCompactLayout()
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<DateRange | undefined>(range)

  const presetRange = (preset: (typeof PRESETS)[number]): DateRange => {
    const now = new Date()
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1)
    switch (preset) {
      case 'today':
        return { from: now, to: now }
      case 'thisMonth':
        return { from: startOfMonth, to: now }
      case 'lastMonth':
        return { from: new Date(now.getFullYear(), now.getMonth() - 1, 1), to: new Date(now.getFullYear(), now.getMonth(), 0) }
      case 'last3Months':
        return { from: new Date(now.getFullYear(), now.getMonth() - 2, 1), to: now }
      case 'thisYear':
      default:
        return { from: new Date(now.getFullYear(), 0, 1), to: now }
    }
  }

  const apply = () => {
    onRangeChange?.(draft)
    setOpen(false)
  }

  return (
    <div className={cn('flex flex-wrap items-center gap-1', className)}>
      <Button variant="ghost" size="icon-sm" onClick={onPrev} aria-label={t('dashboard.monthPrev')}>
        <ChevronLeft className="size-4" aria-hidden="true" />
      </Button>

      <Popover
        open={open}
        onOpenChange={(next) => {
          setOpen(next)
          if (next) setDraft(range)
        }}
      >
        <PopoverTrigger asChild>
          <button
            type="button"
            className={cn(
              'flex h-[34px] items-center gap-2 rounded-sm border border-stroke-control bg-surface-2 px-2.5',
              'text-label font-medium capitalize text-fg-primary transition-colors duration-fast',
              'hover:bg-surface-3/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-ring)]',
            )}
            aria-label={t('period.choose')}
          >
            <CalendarRange className="size-4 text-fg-tertiary" aria-hidden="true" />
            <span className="whitespace-nowrap">{label}</span>
          </button>
        </PopoverTrigger>

        <PopoverContent className="w-auto max-w-[calc(100vw-1.5rem)] overflow-auto p-3" align="start">
          <div className="mb-2 flex flex-wrap gap-1.5">
            {PRESETS.map((preset) => (
              <Button
                key={preset}
                variant="subtle"
                size="sm"
                className="h-7 text-caption"
                onClick={() => setDraft(presetRange(preset))}
              >
                {t(`period.${preset}`)}
              </Button>
            ))}
          </div>

          <DayPicker
            mode="range"
            selected={draft}
            onSelect={setDraft}
            numberOfMonths={compact ? 1 : 2}
            defaultMonth={defaultMonth ?? range?.from ?? new Date()}
            locale={locale === 'ru' ? ru : enUS}
            weekStartsOn={1}
            showOutsideDays
            className="rdp-glass"
          />

          <div className="mt-2 flex items-center justify-between gap-2 border-t border-stroke-subtle pt-2">
            <p className="text-caption text-fg-tertiary">
              {draft?.from
                ? draft.to
                  ? `${draft.from.toLocaleDateString(locale === 'ru' ? 'ru-RU' : 'en-US')} — ${draft.to.toLocaleDateString(locale === 'ru' ? 'ru-RU' : 'en-US')}`
                  : draft.from.toLocaleDateString(locale === 'ru' ? 'ru-RU' : 'en-US')
                : t('period.empty')}
            </p>
            <div className="flex gap-1.5">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setDraft(undefined)
                  onRangeChange?.(undefined)
                  setOpen(false)
                }}
              >
                {t('common.reset')}
              </Button>
              <Button size="sm" onClick={apply}>
                {t('period.apply')}
              </Button>
            </div>
          </div>
        </PopoverContent>
      </Popover>

      <Button variant="ghost" size="icon-sm" onClick={onNext} aria-label={t('dashboard.monthNext')}>
        <ChevronRight className="size-4" aria-hidden="true" />
      </Button>
    </div>
  )
}
