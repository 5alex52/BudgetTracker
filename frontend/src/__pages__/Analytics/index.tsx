import { useMemo, useState } from 'react'
import { Info } from 'lucide-react'
import { useI18n } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import { analyticsApi } from '@/api'
import {
  toAnalyticsRows,
  toBalancePoints,
  toCashflowPoints,
  toDonutSegments,
  toAccountShares,
} from '@/api/mappers'
import { useApiQuery } from '@/hooks/useApi'
import { useFinanceStore } from '@/store/finance'
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

/**
 * «Аналитика»: отчёт месяцы × категории, динамика баланса, денежный поток
 * и структура расходов.
 *
 * Все четыре вкладки живут на одном приложении аналитики: матрица — это
 * `/analytics/matrix`, линии и столбцы — `/analytics/timeseries`, доли —
 * `/analytics/by-category` и `/analytics/by-account`.
 */
export function AnalyticsPage() {
  const { t, locale } = useI18n()
  const { isDark } = useTheme()
  const baseCurrency = useFinanceStore((state) => state.baseCurrency)

  const [tab, setTab] = useState<TabKey>('report')
  const [monthCount, setMonthCount] = useState(6)
  const [txType, setTxType] = useState<'expense' | 'income'>('expense')
  const [range, setRange] = useState<import('react-day-picker').DateRange | undefined>(undefined)

  const startDate = range?.from ? range.from.toISOString().slice(0, 10) : undefined
  const endDate = range?.to ? range.to.toISOString().slice(0, 10) : undefined

  /* Матрица по месяцам + итоги периода */
  const matrix = useApiQuery(
    () => analyticsApi.getMatrix({ months: monthCount, type: txType, rollup: true }),
    [monthCount, txType],
  )
  const summary = useApiQuery(
    () => analyticsApi.getSummary({ startDate, endDate, compare: true }),
    [startDate, endDate],
  )

  /* Три временных ряда: остаток, поток и структура расходов */
  const balanceSeries = useApiQuery(
    () => analyticsApi.getTimeseries({ metric: 'balance', groupBy: 'week', startDate, endDate }),
    [startDate, endDate],
  )
  const cashflowSeries = useApiQuery(
    () => analyticsApi.getTimeseries({ metric: 'cashflow', groupBy: 'week', startDate, endDate }),
    [startDate, endDate],
  )
  const expenseStructure = useApiQuery(
    () => analyticsApi.getByCategory({ type: 'expense', startDate, endDate }),
    [startDate, endDate],
  )
  const accountShares = useApiQuery(() => analyticsApi.getByAccount({ startDate, endDate }), [
    startDate,
    endDate,
  ])

  const report = matrix.data ? toAnalyticsRows(matrix.data) : { months: [], rows: [] }
  const balancePoints = balanceSeries.data ? toBalancePoints(balanceSeries.data, locale) : []
  const cashflowPoints = cashflowSeries.data ? toCashflowPoints(cashflowSeries.data, locale) : []
  const segments = expenseStructure.data ? toDonutSegments(expenseStructure.data.items, 6) : []
  const shares = accountShares.data ? toAccountShares(accountShares.data.items) : []

  const monthLabel = useMemo(
    () => (key: string) =>
      new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
        month: 'short',
        year: '2-digit',
      }).format(new Date(`${key}-01T00:00:00`)),
    [locale],
  )

  const totals = summary.data
  const change = summary.data?.change
  /* Для отчёта показываем не больше 14 строк — как в референсе */
  const visibleRows = report.rows.slice(0, 14)

  return (
    <AppShell
      header={
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-title font-semibold tracking-snug text-fg-primary">{t('analytics.title')}</h1>
          <SegmentedControl
            aria-label={t('recordForm.type')}
            value={txType}
            onValueChange={(value) => setTxType(value as 'expense' | 'income')}
            items={[
              { value: 'expense', label: t('recordForm.expense') },
              { value: 'income', label: t('recordForm.income') },
            ]}
          />
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
        <SummaryTile
          label={t('analytics.totalIncome')}
          value={totals?.income ?? 0}
          currency={baseCurrency}
          trend={change?.income ?? undefined}
        />
        <SummaryTile
          label={t('analytics.totalExpense')}
          value={-(totals?.expense ?? 0)}
          currency={baseCurrency}
          trend={change?.expense ?? undefined}
        />
        <SummaryTile
          label={t('dashboard.cashflowTitle')}
          value={totals?.net ?? 0}
          currency={baseCurrency}
          trend={change?.net ?? undefined}
        />
        <SummaryTile
          label={t('records.total')}
          value={totals?.transactions_count ?? 0}
          currency={t('records.found', { count: totals?.transactions_count ?? 0 }).replace(/\d+/g, '').trim()}
        />
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

            <div className="flex flex-wrap items-center gap-2">
              <SegmentedControl
                aria-label={t('records.total')}
                value={String(monthCount)}
                onValueChange={(value) => setMonthCount(Number(value))}
                items={[
                  { value: '3', label: '3' },
                  { value: '6', label: '6' },
                  { value: '12', label: '12' },
                ]}
              />
              <PeriodPicker
                label={
                  report.months.length > 1
                    ? `${monthLabel(report.months[report.months.length - 1] ?? '')} — ${monthLabel(report.months[0] ?? '')}`
                    : t('records.total')
                }
                onPrev={() => setMonthCount((value) => Math.min(value + 3, 24))}
                onNext={() => setMonthCount((value) => Math.max(value - 3, 3))}
                range={range}
                onRangeChange={setRange}
                defaultMonth={new Date()}
              />
            </div>
          </div>

          {matrix.loading && report.rows.length === 0 && (
            <p className="px-4 py-10 text-center text-label text-fg-tertiary" role="status">
              {t('state.loading')}
            </p>
          )}

          {!matrix.loading && report.rows.length === 0 && (
            <p className="px-4 py-10 text-center text-label text-fg-tertiary">{t('state.empty')}</p>
          )}

          {report.rows.length > 0 && (
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
                    {report.months.map((month) => (
                      <th
                        key={month}
                        scope="col"
                        className="border-b border-stroke-subtle px-3 py-2 text-right text-caption font-medium uppercase tracking-wide text-fg-tertiary"
                      >
                        {monthLabel(month)}
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
                      {report.months.map((month, monthIndex) => (
                        <td
                          key={`${row.id}-${month}`}
                          className={cn('px-3 py-2 text-right', index > 0 && 'border-t border-stroke-subtle')}
                        >
                          <span className="inline-flex items-center justify-end gap-1.5">
                            {monthIndex === 0 && row.trends[0] !== 0 && <TrendBadge value={row.trends[0] ?? 0} />}
                            <Amount
                              value={row.values[monthIndex] ?? 0}
                              size="sm"
                              tone="neutral"
                              className="text-fg-primary"
                            />
                          </span>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {tab === 'balance' && (
        <div className="grid gap-4 lg:grid-cols-[1.5fr_1fr]">
          <Card>
            <CardHeader title={t('analytics.tab.balance')} subtitle={t('dashboard.vsPrevious')} />
            {balancePoints.length > 1 ? (
              <div className="mt-4">
                <LineChart points={balancePoints} ariaLabel={t('analytics.tab.balance')} height={220} />
              </div>
            ) : (
              <p className="mt-4 text-caption text-fg-tertiary">
                {balanceSeries.loading ? t('state.loading') : t('state.empty')}
              </p>
            )}
          </Card>

          {/* Доли счетов: видно, где лежат деньги */}
          <Card>
            <CardHeader title={t('nav.accounts')} />
            <ul className="mt-3 space-y-2">
              {shares.length === 0 && <li className="text-caption text-fg-tertiary">{t('state.empty')}</li>}
              {shares.map((share) => (
                <li key={share.account_id} className="flex items-center gap-2 text-caption">
                  <span
                    className="size-2 shrink-0 rounded-pill"
                    style={{ backgroundColor: share.tint }}
                    aria-hidden="true"
                  />
                  <span className="min-w-0 flex-1 truncate text-fg-secondary">{share.name}</span>
                  <span className="text-fg-tertiary">{share.transactions_count}</span>
                  <Amount value={-Math.abs(share.expense)} size="xs" tone="neutral" />
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}

      {tab === 'cashflow' && (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card>
            <CardHeader title={t('analytics.tab.cashflow')} subtitle={t('dashboard.incomes')} />
            {cashflowPoints.length > 0 ? (
              <div className="mt-4">
                <BarChart points={cashflowPoints} ariaLabel={t('analytics.tab.cashflow')} height={220} />
              </div>
            ) : (
              <p className="mt-4 text-caption text-fg-tertiary">
                {cashflowSeries.loading ? t('state.loading') : t('state.empty')}
              </p>
            )}
          </Card>
          <Card>
            <CardHeader title={t('dashboard.expenseStructure')} subtitle={t('dashboard.spendingCharacter')} />
            {segments.length > 0 ? (
              <div className="mt-4 flex justify-center">
                <DonutChart segments={segments} ariaLabel={t('dashboard.expenseStructure')} size={200} />
              </div>
            ) : (
              <p className="mt-4 text-caption text-fg-tertiary">{t('state.empty')}</p>
            )}
          </Card>
        </div>
      )}

      {tab === 'advanced' && (
        <Card className="p-8 text-center">
          <p className="text-headline font-semibold text-fg-primary">{t('analytics.tab.advanced')}</p>
          <p className="mx-auto mt-2 max-w-md text-label text-fg-secondary">{t('dashboard.upgradeHint')}</p>
          <Button className="mt-4">{t('dashboard.upgradePremium')}</Button>
        </Card>
      )}
    </AppShell>
  )
}

function SummaryTile({
  label,
  value,
  currency,
  trend,
}: {
  label: string
  value: number
  currency?: string
  trend?: number
}) {
  return (
    <Card className="p-4">
      <p className="text-caption text-fg-tertiary">{label}</p>
      <div className="mt-1 flex items-baseline justify-between gap-2">
        <Amount value={value} currency={currency} size="md" tone="neutral" className="text-fg-primary" />
        {typeof trend === 'number' && trend !== 0 && <TrendBadge value={trend} />}
      </div>
    </Card>
  )
}
