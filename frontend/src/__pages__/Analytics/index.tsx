import { Fragment, useMemo, useState } from 'react'
import { CheckCircle2, ChevronDown, ChevronRight, Download, Info } from 'lucide-react'
import { useI18n } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import type { MatrixDto, MatrixRowDto } from '@/api/types'
import { analyticsApi } from '@/api'
import {
  toBalancePoints,
  toCashflowPoints,
  toDonutSegments,
  toAccountShares,
  toBarSegments,
} from '@/api/mappers'
import { useApiQuery } from '@/hooks/useApi'
import { useFinanceStore } from '@/store/finance'
import { AppShell } from '@/components/layout/AppShell'
import { Amount, TrendBadge } from '@/components/data/Amount'
import { Card, CardHeader } from '@/components/ui/card'
import { SegmentedControl } from '@/components/ui/toggles'
import { Button } from '@/components/ui/button'
import { PeriodPicker } from '@/components/data/PeriodPicker'
import { readableOnTint } from '@/__shared__/utils/contrast'
import { useTheme } from '@/hooks/useTheme'
import { BarChart, DonutChart, LineChart } from '@/components/charts/charts'
import { CategoryIcon } from '@/__shared__/utils/category-icon'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/overlays'
import { QueryError } from '@/components/data/QueryError'

type TabKey = 'report' | 'balance' | 'cashflow' | 'advanced'

type ReportRow = {
  id: string
  name: string
  icon?: string
  color?: string
  values: number[]
  trends: Array<number | null>
  children: ReportRow[]
}

type ReportSection = {
  key: 'income' | 'expense'
  total: ReportRow
  rows: ReportRow[]
}

type CategoryMeta = { name: string; icon: string | null; color: string | null }

/** Процент к предыдущему месяцу; для первого месяца базы нет. */
function trendSeries(values: number[]): Array<number | null> {
  return values.map((value, index) => {
    if (index === 0) return null
    const previous = values[index - 1]
    if (!previous) return null
    return Math.round(((value - previous) / Math.abs(previous)) * 10000) / 100
  })
}

function sumSeries(series: number[][]): number[] {
  return series[0]?.map((_, index) => series.reduce((sum, values) => sum + (values[index] ?? 0), 0)) ?? []
}

function toReportRow(
  id: string,
  meta: CategoryMeta,
  values: number[],
  sign: 1 | -1,
  children: ReportRow[] = [],
): ReportRow {
  return {
    id,
    name: meta.name,
    icon: meta.icon ?? undefined,
    color: meta.color ?? undefined,
    values: values.map((value) => value * sign),
    trends: trendSeries(values),
    children,
  }
}

/** Родители собираются из подкатегорий: строка родителя может быть без прямых трат. */
function buildReportSection(
  matrix: MatrixDto,
  key: 'income' | 'expense',
  totalLabel: string,
  metaById: Map<number, CategoryMeta>,
): ReportSection {
  const sign = key === 'expense' ? -1 : 1
  const rows = matrix.rows.filter(
    (row): row is MatrixRowDto & { category_id: number } => row.category_id !== null,
  )
  const byId = new Map(rows.map((row) => [row.category_id, row]))
  const parentIds = new Set(rows.map((row) => row.parent_id ?? row.category_id))

  const parents: ReportRow[] = []
  for (const parentId of parentIds) {
    const parent = byId.get(parentId)
    const children = rows.filter((row) => row.parent_id === parentId)
    const meta = parent
      ? { name: parent.name, icon: parent.icon, color: parent.color }
      : metaById.get(parentId)
    if (!meta) continue

    const combined = sumSeries([
      parent?.values ?? matrix.months.map(() => 0),
      ...children.map((row) => row.values),
    ])
    const visibleChildren = children
      .map((child) =>
        toReportRow(
          `${key}-${child.category_id}`,
          {
            name: child.name,
            icon: child.icon,
            color: child.color,
          },
          child.values,
          sign,
        ),
      )
      .filter((child) => child.values.slice(1).some((value) => value !== 0))
      .sort((left, right) => right.values.reduce((sum, value) => sum + Math.abs(value), 0) - left.values.reduce((sum, value) => sum + Math.abs(value), 0))

    if (!combined.slice(1).some((value) => value !== 0) && visibleChildren.length === 0) continue
    parents.push(toReportRow(`${key}-${parentId}`, meta, combined, sign, visibleChildren))
  }

  parents.sort(
    (left, right) =>
      right.values.reduce((sum, value) => sum + Math.abs(value), 0) -
      left.values.reduce((sum, value) => sum + Math.abs(value), 0),
  )

  const totalValues = sumSeries(rows.map((row) => row.values))
  return {
    key,
    total: toReportRow(`${key}-total`, { name: totalLabel, icon: null, color: null }, totalValues, sign),
    rows: parents,
  }
}

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
  const categories = useFinanceStore((state) => state.categories)

  const [tab, setTab] = useState<TabKey>('report')
  const [monthCount, setMonthCount] = useState(6)
  const [reportOffset, setReportOffset] = useState(0)
  const [range, setRange] = useState<import('react-day-picker').DateRange | undefined>(undefined)

  const startDate = range?.from ? range.from.toISOString().slice(0, 10) : undefined
  const endDate = range?.to ? range.to.toISOString().slice(0, 10) : undefined

  /* Конец месяца отчёта: текущий или сдвинутый стрелками назад. */
  const reportEndDate = useMemo(() => {
    if (range?.to) return range.to.toISOString().slice(0, 10)
    const date = new Date()
    date.setDate(1)
    date.setMonth(date.getMonth() + reportOffset + 1)
    date.setDate(0)
    return date.toISOString().slice(0, 10)
  }, [range?.to, reportOffset])

  /*
   * Для тренда первого видимого месяца нужен ещё один месяц слева —
   * поэтому запрашиваем на один месяц больше, чем показываем.
   */
  const reportMonths = monthCount + 1
  const expenseMatrix = useApiQuery(
    () => analyticsApi.getMatrix({ months: reportMonths, type: 'expense', rollup: false, endDate: reportEndDate }),
    [reportMonths, reportEndDate],
  )
  const incomeMatrix = useApiQuery(
    () => analyticsApi.getMatrix({ months: reportMonths, type: 'income', rollup: false, endDate: reportEndDate }),
    [reportMonths, reportEndDate],
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
  const incomeStructure = useApiQuery(
    () => analyticsApi.getByCategory({ type: 'income', startDate, endDate }),
    [startDate, endDate],
  )
  const accountShares = useApiQuery(() => analyticsApi.getByAccount({ startDate, endDate }), [
    startDate,
    endDate,
  ])

  const report = useMemo(() => {
    const source = expenseMatrix.data ?? incomeMatrix.data
    const metaById = new Map<number, CategoryMeta>()
    categories.forEach((category) =>
      metaById.set(category.id, { name: category.name, icon: category.icon, color: category.color }),
    )
    ;[incomeMatrix.data, expenseMatrix.data].forEach((matrix) =>
      matrix?.rows.forEach((row) => {
        if (row.category_id !== null) {
          metaById.set(row.category_id, { name: row.name, icon: row.icon, color: row.color })
        }
      }),
    )

    const sections: ReportSection[] = []
    if (incomeMatrix.data) {
      sections.push(buildReportSection(incomeMatrix.data, 'income', t('analytics.totalIncome'), metaById))
    }
    if (expenseMatrix.data) {
      sections.push(buildReportSection(expenseMatrix.data, 'expense', t('analytics.totalExpense'), metaById))
    }
    return { months: source?.months.slice(1) ?? [], sections }
  }, [categories, expenseMatrix.data, incomeMatrix.data, t])

  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const toggleExpanded = (id: string) =>
    setExpanded((current) => {
      const next = new Set(current)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  const balancePoints = balanceSeries.data ? toBalancePoints(balanceSeries.data, locale) : []
  const cashflowPoints = cashflowSeries.data ? toCashflowPoints(cashflowSeries.data, locale) : []
  const segments = expenseStructure.data ? toDonutSegments(expenseStructure.data.items, 6) : []
  const incomeSegments = incomeStructure.data ? toBarSegments(incomeStructure.data.items, 6) : []
  const expenseSegments = expenseStructure.data ? toBarSegments(expenseStructure.data.items, 6) : []
  const shares = accountShares.data ? toAccountShares(accountShares.data.items) : []

  const monthLabel = useMemo(
    () => (key: string) => {
      if (!key) return ''
      const date = new Date(`${key}-01T00:00:00`)
      const month = new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
        month: 'long',
      }).format(date)
      return `${month} ${date.getFullYear()}`
    },
    [locale],
  )

  const totals = summary.data
  const change = summary.data?.change

  const exportReport = () => {
    const escape = (value: string | number) => `"${String(value).replace(/"/g, '""')}"`
    const lines: Array<Array<string | number>> = [['', ...report.months.map((month) => monthLabel(month))]]
    report.sections.forEach((section) => {
      const push = (row: ReportRow, prefix = '') => {
        lines.push([prefix + row.name, ...report.months.map((_, index) => row.values[index + 1] ?? 0)])
        row.children.forEach((child) => push(child, `${prefix}  `))
      }
      push(section.total)
      section.rows.forEach((row) => push(row))
    })
    const csv = '\uFEFF' + lines.map((line) => line.map(escape).join(';')).join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `analytics-${report.months[0] ?? 'report'}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

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
      <QueryError
        error={
          incomeMatrix.error ??
          expenseMatrix.error ??
          summary.error ??
          balanceSeries.error ??
          cashflowSeries.error ??
          expenseStructure.error
        }
        className="mb-4"
      />

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
              <Button variant="glass" size="sm" className="gap-1.5" onClick={exportReport}>
                <Download className="size-4" aria-hidden="true" />
                {t('records.export')}
              </Button>
              <PeriodPicker
                label={
                  report.months.length > 1
                    ? `${monthLabel(report.months[0] ?? '')} — ${monthLabel(report.months[report.months.length - 1] ?? '')}`
                    : t('records.total')
                }
                onPrev={() => {
                  setRange(undefined)
                  setReportOffset((value) => value - 1)
                }}
                onNext={() => {
                  setRange(undefined)
                  setReportOffset((value) => Math.min(value + 1, 0))
                }}
                range={range}
                onRangeChange={setRange}
                defaultMonth={new Date(`${reportEndDate}T00:00:00`)}
              />
            </div>
          </div>

          {(incomeMatrix.loading || expenseMatrix.loading) && report.months.length === 0 && (
            <p className="px-4 py-10 text-center text-label text-fg-tertiary" role="status">
              {t('state.loading')}
            </p>
          )}

          {!incomeMatrix.loading && !expenseMatrix.loading && report.sections.length === 0 && (
            <p className="px-4 py-10 text-center text-label text-fg-tertiary">{t('state.empty')}</p>
          )}

          {report.sections.length > 0 && (
            <div className="overflow-x-auto">
              {report.sections.map((section) => (
                <table key={section.key} className="w-full min-w-[720px] border-collapse text-label">
                  <caption className="sr-only">{section.total.name}</caption>
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
                    <tr className="group bg-surface-2/40 transition-colors duration-fast hover:bg-surface-2/60">
                      <th
                        scope="row"
                        className="sticky left-0 z-[1] bg-surface-2/90 px-4 py-2.5 text-left text-label font-semibold text-fg-primary group-hover:bg-surface-2/90"
                      >
                        <span className="flex items-center gap-2">
                          <span className="grid size-6 shrink-0 place-items-center rounded-pill bg-accent/15 text-accent">
                            <CheckCircle2 className="size-3.5" aria-hidden="true" />
                          </span>
                          {section.total.name}
                        </span>
                      </th>
                      {report.months.map((month, index) => (
                        <td key={`${section.key}-total-${month}`} className="px-3 py-2.5 text-right">
                          <span className="flex flex-col items-end gap-0.5">
                            <Amount
                              value={section.total.values[index + 1] ?? 0}
                              size="sm"
                              tone="auto"
                            />
                            {(section.total.trends[index + 1] ?? 0) !== 0 && (
                              <TrendBadge
                                value={section.total.trends[index + 1] ?? 0}
                                invert={section.key === 'expense'}
                              />
                            )}
                          </span>
                        </td>
                      ))}
                    </tr>

                    {section.rows.map((row) => (
                      <Fragment key={row.id}>
                        <tr className="group transition-colors duration-fast hover:bg-surface-2/60">
                          <th
                            scope="row"
                            className="sticky left-0 z-[1] border-t border-stroke-subtle bg-surface-1 px-4 py-2 text-left text-label font-medium text-fg-primary group-hover:bg-surface-2"
                          >
                            <button
                              type="button"
                              onClick={() => row.children.length > 0 && toggleExpanded(row.id)}
                              aria-expanded={row.children.length > 0 ? expanded.has(row.id) : undefined}
                              className={cn(
                                'flex w-full items-center gap-2 text-left',
                                row.children.length > 0 ? 'cursor-pointer' : 'cursor-default',
                              )}
                            >
                              {row.children.length > 0 ? (
                                expanded.has(row.id) ? (
                                  <ChevronDown className="size-3.5 shrink-0 text-fg-tertiary" aria-hidden="true" />
                                ) : (
                                  <ChevronRight className="size-3.5 shrink-0 text-fg-tertiary" aria-hidden="true" />
                                )
                              ) : (
                                <span className="size-3.5 shrink-0" aria-hidden="true" />
                              )}
                              <span
                                className="grid size-6 shrink-0 place-items-center rounded-pill"
                                style={{
                                  backgroundColor: `${row.color ?? '#888'}22`,
                                  color: readableOnTint(row.color ?? '#888', { dark: isDark, threshold: 3 }),
                                }}
                              >
                                <CategoryIcon name={row.icon ?? 'circle'} className="size-3.5" />
                              </span>
                              {row.name}
                            </button>
                          </th>
                          {report.months.map((month, index) => (
                            <td
                              key={`${row.id}-${month}`}
                              className="border-t border-stroke-subtle px-3 py-2 text-right"
                            >
                              <span className="flex flex-col items-end gap-0.5">
                                <Amount value={row.values[index + 1] ?? 0} size="sm" tone="auto" />
                                {(row.trends[index + 1] ?? 0) !== 0 && (
                                  <TrendBadge
                                    value={row.trends[index + 1] ?? 0}
                                    invert={section.key === 'expense'}
                                  />
                                )}
                              </span>
                            </td>
                          ))}
                        </tr>

                        {expanded.has(row.id) &&
                          row.children.map((child) => (
                            <tr
                              key={child.id}
                              className="group transition-colors duration-fast hover:bg-surface-2/40"
                            >
                              <th
                                scope="row"
                                className="sticky left-0 z-[1] border-t border-stroke-subtle bg-surface-1 py-1.5 pl-12 pr-4 text-left text-label font-normal text-fg-secondary group-hover:bg-surface-2"
                              >
                                <span className="flex items-center gap-2">
                                  <span
                                    className="size-1.5 shrink-0 rounded-pill"
                                    style={{ backgroundColor: child.color ?? '#888' }}
                                    aria-hidden="true"
                                  />
                                  {child.name}
                                </span>
                              </th>
                              {report.months.map((month, index) => (
                                <td
                                  key={`${child.id}-${month}`}
                                  className="border-t border-stroke-subtle px-3 py-1.5 text-right"
                                >
                                  <span className="flex flex-col items-end gap-0.5">
                                    <Amount value={child.values[index + 1] ?? 0} size="xs" tone="auto" />
                                    {(child.trends[index + 1] ?? 0) !== 0 && (
                                      <TrendBadge
                                        value={child.trends[index + 1] ?? 0}
                                        invert={section.key === 'expense'}
                                      />
                                    )}
                                  </span>
                                </td>
                              ))}
                            </tr>
                          ))}
                      </Fragment>
                    ))}
                  </tbody>
                </table>
              ))}
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
        <div className="space-y-4">
          <>
              {/* Сравнение с предыдущим периодом */}
              <Card className="p-4">
                <CardHeader title={t('dashboard.periodComparison')} subtitle={t('dashboard.vsPrevious')} />
                {totals?.previous ? (
                  <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <div className="flex flex-col gap-1">
                      <span className="text-overline uppercase text-fg-tertiary">{t('analytics.totalIncome')}</span>
                      <div className="flex items-baseline gap-2">
                        <Amount value={totals.income ?? 0} currency={baseCurrency} size="md" tone="positive" />
                        {typeof change?.income === 'number' && change.income !== 0 && (
                          <TrendBadge value={change.income} />
                        )}
                      </div>
                      <span className="text-caption text-fg-tertiary">
                        {t('analytics.vsPrevious', { value: totals.previous.income })}
                      </span>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-overline uppercase text-fg-tertiary">{t('analytics.totalExpense')}</span>
                      <div className="flex items-baseline gap-2">
                        <Amount value={-(totals.expense ?? 0)} currency={baseCurrency} size="md" tone="negative" />
                        {typeof change?.expense === 'number' && change.expense !== 0 && (
                          <TrendBadge value={change.expense} />
                        )}
                      </div>
                      <span className="text-caption text-fg-tertiary">
                        {t('analytics.vsPrevious', { value: -totals.previous.expense })}
                      </span>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-overline uppercase text-fg-tertiary">{t('dashboard.cashflowTitle')}</span>
                      <div className="flex items-baseline gap-2">
                        <Amount value={totals.net ?? 0} currency={baseCurrency} size="md" tone="neutral" />
                        {typeof change?.net === 'number' && change.net !== 0 && (
                          <TrendBadge value={change.net} />
                        )}
                      </div>
                      <span className="text-caption text-fg-tertiary">
                        {t('analytics.vsPrevious', { value: totals.previous.net })}
                      </span>
                    </div>
                  </div>
                ) : (
                  <p className="mt-4 text-caption text-fg-tertiary">{t('state.empty')}</p>
                )}
              </Card>

              {/* Доходы по категориям */}
              <div className="grid gap-4 lg:grid-cols-2">
                <Card>
                  <CardHeader title={t('dashboard.incomes')} subtitle={t('analytics.byCategory')} />
                  {incomeSegments.length > 0 ? (
                    <div className="mt-4 space-y-2">
                      {incomeSegments.map((seg) => (
                        <div key={seg.label} className="flex items-center gap-2">
                          <span className="min-w-0 flex-1 truncate text-caption text-fg-secondary">{seg.label}</span>
                          <Amount value={seg.value} currency={baseCurrency} size="sm" tone="positive" />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-4 text-caption text-fg-tertiary">
                      {incomeStructure.loading ? t('state.loading') : t('state.empty')}
                    </p>
                  )}
                </Card>

                {/* Расходы по категориям */}
                <Card>
                  <CardHeader title={t('dashboard.expenses')} subtitle={t('analytics.byCategory')} />
                  {expenseSegments.length > 0 ? (
                    <div className="mt-4 space-y-2">
                      {expenseSegments.map((seg) => (
                        <div key={seg.label} className="flex items-center gap-2">
                          <span className="min-w-0 flex-1 truncate text-caption text-fg-secondary">{seg.label}</span>
                          <Amount value={-seg.value} currency={baseCurrency} size="sm" tone="negative" />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-4 text-caption text-fg-tertiary">
                      {expenseStructure.loading ? t('state.loading') : t('state.empty')}
                    </p>
                  )}
                </Card>
              </div>

              {/* Дополнительные графики */}
              <div className="grid gap-4 lg:grid-cols-2">
                <Card>
                  <CardHeader title={t('analytics.categoryTrends')} subtitle={t('analytics.last3Months')} />
                  <div className="mt-4 space-y-2">
                    {expenseStructure.data?.items.slice(0, 5).map((item) => (
                      <div key={item.category_id} className="space-y-1">
                        <div className="flex items-center justify-between text-caption">
                          <span className="text-fg-secondary">{item.name}</span>
                          <Amount value={item.total} currency={baseCurrency} size="xs" tone="negative" />
                        </div>
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              backgroundColor: item.color || undefined,
                              width: `${(item.total / (expenseStructure.data?.total ?? 1)) * 100}%`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>

                <Card>
                  <CardHeader title={t('analytics.accountActivity')} subtitle={t('analytics.transactionsByAccount')} />
                  <div className="mt-4 space-y-2">
                    {shares.map((share) => (
                      <div key={share.account_id} className="flex items-center gap-3">
                        <span
                          className="h-2 w-2 rounded-full"
                          style={{ backgroundColor: share.tint }}
                          aria-hidden="true"
                        />
                        <span className="min-w-0 flex-1 truncate text-caption text-fg-secondary">
                          {share.name}
                        </span>
                        <span className="text-caption text-fg-tertiary">{share.transactions_count}</span>
                      </div>
                    ))}
                  </div>
                </Card>
              </div>
            </>
        </div>
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
