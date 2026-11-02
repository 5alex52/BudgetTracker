import { useState } from 'react'
import {Info} from 'lucide-react'
import { useI18n } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import {
  analyticsMonths,
  analyticsRows,
  balanceSeries,
  cashflowSeries,
  expenseStructure,
} from '@/__shared__/mock/finance'
import { AppShell } from '@/components/layout/AppShell'
import { Amount, TrendBadge } from '@/components/data/Amount'
import { Card, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { SegmentedControl } from '@/components/ui/toggles'
import { PeriodPicker } from '@/components/data/PeriodPicker'
import { readableOnTint } from '@/__shared__/utils/contrast'
import { useTheme } from '@/hooks/useTheme'
import { BarChart, DonutChart, LineChart } from '@/components/charts/charts'
import { CategoryIcon } from '@/__shared__/utils/category-icon'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/overlays'

type TabKey = 'report' | 'balance' | 'cashflow' | 'advanced'

/** «Аналитика»: четыре вкладки из референса, таблица месяцы × категории со sticky-колонкой. */
export function AnalyticsPage() {
  const { t, locale } = useI18n()
  const { isDark } = useTheme()
  const [tab, setTab] = useState<TabKey>('report')
  const [monthTo, setMonthTo] = useState(2)
  const [range, setRange] = useState<import('react-day-picker').DateRange | undefined>(undefined)

  /** Окно всегда в 3 месяца — как строка периодов в референсе. */
  const months = analyticsMonths.slice(monthTo, monthTo + 3).reverse()
  const monthLabel = (key: string) => {
    const found = analyticsMonths.find((month) => month.key === key)
    if (!found) return key
    return locale === 'ru' ? found.label : found.labelEn
  }

  const visibleRows = analyticsRows.slice(0, 14)
  const income = analyticsRows.find((row) => row.id === 'total-income')
  const expense = analyticsRows.find((row) => row.id === 'total-expense')

  return (
    <AppShell
      header={
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-title font-semibold tracking-snug text-fg-primary">{t('analytics.title')}</h1>
        </div>
      }
    >
      {/* Вкладки: на мобиле прокручиваются горизонтально, без переноса строк */}
      <div className="mb-4 overflow-x-auto pb-1">
        <div className="min-w-max">
          <SegmentedControl
            aria-label={t('analytics.title')}
            value={tab}
            onValueChange={(value) => setTab(value as TabKey)}
            items={[
              { value: 'report', label: t('analytics.tab.report') },
              { value: 'balance', label: t('analytics.tab.balance') },
              { value: 'cashflow', label: t('analytics.tab.cashflow') },
              { value: 'advanced', label: t('analytics.tab.advanced') },
            ]}
          />
        </div>
      </div>

      {/* Итоги периода */}
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryTile label={t('analytics.totalIncome')} value={income?.values[0] ?? 0} trend={income?.trends[0]} />
        <SummaryTile
          label={t('analytics.totalExpense')}
          value={expense?.values[0] ?? 0}
          trend={expense?.trends[0]}
          negative
        />
        <SummaryTile
          label={t('dashboard.balance')}
          value={balanceSeries[balanceSeries.length - 1]?.value ?? 0}
          trend={12}
        />
        <SummaryTile label={t('dashboard.cashflowTitle')} value={cashflowSeries[0]?.income ?? 0} trend={8} />
      </div>

      {tab === 'report' && (
        <Card className="overflow-hidden p-0">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stroke-subtle px-4 py-2.5">
            <div className="flex items-center gap-1.5">
              <h2 className="text-label font-semibold text-fg-primary">{t('analytics.tab.report')}</h2>
              <Popover>
                <PopoverTrigger asChild>
                  <button
                    type="button"
                    className="text-fg-tertiary transition-colors hover:text-fg-secondary"
                    aria-label={t('filters.info')}
                  >
                    <Info className="size-3.5" aria-hidden="true" />
                  </button>
                </PopoverTrigger>
                <PopoverContent className="max-w-xs">
                  <p className="text-caption leading-relaxed text-fg-secondary">{t('filters.infoHint')}</p>
                </PopoverContent>
              </Popover>
            </div>

            <PeriodPicker
              label={`${monthLabel(months[months.length - 1]?.key ?? '')} — ${monthLabel(months[0]?.key ?? '')}`}
              onPrev={() => setMonthTo((value) => Math.min(value + 1, analyticsMonths.length - 1))}
              onNext={() => setMonthTo((value) => Math.max(value - 1, 0))}
              range={range}
              onRangeChange={setRange}
              defaultMonth={new Date(2025, 9, 1)}
            />
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[640px] border-collapse text-label">
              <caption className="sr-only">{t('analytics.tab.report')}</caption>
              <thead>
                <tr>
                  <th
                    scope="col"
                    className="sticky left-0 z-[2] border-b border-stroke-subtle bg-surface-1 px-4 py-2 text-left text-caption font-medium uppercase tracking-wide text-fg-tertiary"
                  >
                    {t('analytics.category')}
                  </th>
                  {months.map((month) => (
                    <th
                      key={month.key}
                      scope="col"
                      className="border-b border-stroke-subtle px-3 py-2 text-right text-caption font-medium uppercase tracking-wide text-fg-tertiary"
                    >
                      {monthLabel(month.key)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((row, index) => (
                  <tr key={row.id} className="group transition-colors duration-fast hover:bg-surface-2/60">
                    <th
                      scope="row"
                      className={cn(
                        'sticky left-0 z-[1] bg-surface-1 px-4 py-2 text-left text-label font-medium text-fg-primary',
                        'group-hover:bg-surface-2/60',
                        index > 0 && 'border-t border-stroke-subtle',
                        row.icon && 'flex items-center gap-2',
                      )}
                    >
                      {row.icon && (
                        <span
                          className="grid size-6 shrink-0 place-items-center rounded-pill"
                          style={{
                            backgroundColor: `${row.color ?? '#888'}22`,
                            color: readableOnTint(row.color ?? '#888', { dark: isDark, threshold: 3 }),
                          }}
                        >
                          <CategoryIcon name={row.icon} className="size-3.5" />
                        </span>
                      )}
                      {row.name}
                    </th>
                    {months.map((month, monthIndex) => {
                      const monthPos = analyticsMonths.findIndex((item) => item.key === month.key)
                      const value = row.values[monthPos] ?? 0
                      const trend = row.trends[monthPos] ?? 0
                      return (
                        <td
                          key={`${row.id}-${month.key}`}
                          className={cn(
                            'px-3 py-2 text-right',
                            index > 0 && 'border-t border-stroke-subtle',
                          )}
                        >
                          <span className="inline-flex items-center justify-end gap-1.5">
                            {monthIndex === 0 && trend !== 0 && <TrendBadge value={trend} />}
                            <Amount
                              value={value}
                              size="sm"
                              tone={row.id === 'total-expense' ? 'neutral' : 'neutral'}
                              className="text-fg-primary"
                            />
                          </span>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {tab === 'balance' && (
        <Card>
          <CardHeader title={t('analytics.tab.balance')} subtitle={t('dashboard.vsPrevious')} />
          <div className="mt-4">
            <LineChart points={balanceSeries} ariaLabel={t('analytics.tab.balance')} height={220} />
          </div>
        </Card>
      )}

      {tab === 'cashflow' && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader title={t('analytics.tab.cashflow')} subtitle={t('dashboard.incomes')} />
            <div className="mt-4">
              <BarChart points={cashflowSeries} ariaLabel={t('analytics.tab.cashflow')} height={220} />
            </div>
          </Card>
          <Card>
            <CardHeader title={t('dashboard.expenseStructure')} subtitle={t('dashboard.spendingCharacter')} />
            <div className="mt-4 flex justify-center">
              <DonutChart segments={expenseStructure} ariaLabel={t('dashboard.expenseStructure')} size={200} />
            </div>
          </Card>
        </div>
      )}

      {tab === 'advanced' && (
        <Card className="p-8 text-center">
          <p className="text-headline font-semibold text-fg-primary">{t('analytics.tab.advanced')}</p>
          <p className="mx-auto mt-2 max-w-md text-label text-fg-secondary">
            {t('dashboard.upgradeHint')}
          </p>
          <Button className="mt-4">{t('dashboard.upgradePremium')}</Button>
        </Card>
      )}
    </AppShell>
  )
}

function SummaryTile({
  label,
  value,
  trend,
  negative = false,
}: {
  label: string
  value: number
  trend?: number
  negative?: boolean
}) {
  return (
    <Card className="p-4">
      <p className="text-caption text-fg-tertiary">{label}</p>
      <div className="mt-1 flex items-baseline justify-between gap-2">
        <Amount value={value} size="md" tone={negative ? 'neutral' : 'neutral'} className="text-fg-primary" />
        {typeof trend === 'number' && <TrendBadge value={trend} />}
      </div>
    </Card>
  )
}
