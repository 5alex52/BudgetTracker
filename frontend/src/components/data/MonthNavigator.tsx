import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useI18n } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import { Button } from '@/components/ui/button'

export interface MonthNavigatorProps {
  /** «октябрь 2025» в нужном языке — формируется вызывающим кодом */
  label: string
  onPrev?: () => void
  onNext?: () => void
  className?: string
}

/** Навигатор месяца: ‹ октябрь 2025 ›. */
export function MonthNavigator({ label, onPrev, onNext, className }: MonthNavigatorProps) {
  const { t } = useI18n()

  return (
    <div className={cn('flex items-center gap-1', className)}>
      <Button variant="ghost" size="icon-sm" onClick={onPrev} aria-label={t('dashboard.monthPrev')}>
        <ChevronLeft className="size-4" aria-hidden="true" />
      </Button>
      <span className="min-w-[124px] text-center text-label font-medium capitalize text-fg-primary">
        {label}
      </span>
      <Button variant="ghost" size="icon-sm" onClick={onNext} aria-label={t('dashboard.monthNext')}>
        <ChevronRight className="size-4" aria-hidden="true" />
      </Button>
    </div>
  )
}
