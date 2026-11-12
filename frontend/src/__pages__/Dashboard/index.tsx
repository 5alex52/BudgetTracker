import { useMemo, useState } from 'react'
import { LayoutGrid, MoreHorizontal, Plus, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useI18n } from '@/i18n'
import { accountsApi, analyticsApi } from '@/api'
import { toBalancePoints, toCashflowPoints, toDonutSegments } from '@/api/mappers'
import { useApiQuery } from '@/hooks/useApi'
import { useAuthStore } from '@/store/auth'
import { useFinanceStore } from '@/store/finance'
import { AppShell } from '@/components/layout/AppShell'
import { AccountCard } from '@/components/data/AccountCard'
import { QueryError } from '@/components/data/QueryError'
import { useRecordDialog } from '@/components/records/RecordDialogContext'
import { PeriodPicker } from '@/components/data/PeriodPicker'
import { Amount, TrendBadge } from '@/components/data/Amount'
import { Card, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { BarChart, DonutChart, LineChart } from '@/components/charts/charts'
import { SegmentedControl } from '@/components/ui/toggles'
import { AccountDialog } from '@/components/accounts/AccountDialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/overlays'

/** Base period boundaries: day, week or month shifted back. */
function periodBounds(period: 'day' | 'week' | 'month', offset: number) {
  const iso = (date: Date) => date.toISOString().slice(0, 10)
  const now = new Date()

  if (period === 'day') {
    const day = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset)
    return { start: iso(day), end: iso(day), month: day }
  }
  if (period === 'week') {
    // The week starts on Monday: getDay() returns 0 for Sunday
    const shift = (now.getDay() + 6) % 7
    const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - shift + offset * 7)
    const sunday = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + 6)
    return { start: iso(monday), end: iso(sunday), month: monday }
  }
  return monthBounds(offset)
}

/** Month boundaries by offset from the current one: 0 — this month, −1 — last. */
function monthBounds(offset: number) {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth() + offset, 1)
  const end = new Date(now.getFullYear(), now.getMonth() + offset + 1, 0)
  const iso = (date: Date) => date.toISOString().slice(0, 10)
  return { start: iso(start), end: iso(end), month: start }
}

/**
 * "Overview".
 *
 * All KPIs, charts and the spending breakdown are computed on the server:
 * `/analytics/summary` returns totals and comparison with the previous period,
 * `/analytics/timeseries` — lines and bars, `/analytics/by-category` — shares.
 * The client only lays the responses out into widgets.
 */
export function DashboardPage() {
  const { t, locale } = useI18n()
  const { openCreate: onAddRecord } = useRecordDialog()
  const navigate = useNavigate()

  const accounts = useFinanceStore((state) => state.accounts)
  const baseCurrency = useFinanceStore((state) => state.baseCurrency)

  /* Period: current month by default, an arbitrary range can be picked */
  const [range, setRange] = useState<import('react-day-picker').DateRange | undefined>(undefined)
  const [monthOffset, setMonthOffset] = useState(0)
  const [accountDialogOpen, setAccountDialogOpen] = useState(false)
  const [comparison, setComparison] = useState<'cashflow' | 'expense' | 'income'>('cashflow')
  /** Which KPIs to show: the Customize menu really toggles the tiles */
  const [hiddenKpi, setHiddenKpi] = useState<Array<'balance' | 'cashflow' | 'expenses'>>([])

  /* Base period from settings: day, week or month */
  const savedPeriod = useAuthStore((state) => state.user?.default_period)
  const period: 'day' | 'week' | 'month' =
    savedPeriod === 'day' || savedPeriod === 'week' ? savedPeriod : 'month'

  const bounds = periodBounds(period, monthOffset)
  const startDate = range?.from ? range.from.toISOString().slice(0, 10) : bounds.start
  const endDate = range?.to ? range.to.toISOString().slice(0, 10) : bounds.end

  const monthLabel = new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
    month: 'long',
    year: 'numeric',
  }).format(bounds.month)
  const defaultLabel =
    period === 'month'
      ? monthLabel
      : `${new Date(bounds.start).toLocaleDateString(locale === 'ru' ? 'ru-RU' : 'en-US')} — ${new Date(bounds.end).toLocaleDateString(locale === 'ru' ? 'ru-RU' : 'en-US')}`
  const rangeLabel =
    range?.from && range?.to
      ? `${range.from.toLocaleDateString(locale === 'ru' ? 'ru-RU' : 'en-US')} — ${range.to.toLocaleDateString(locale === 'ru' ? 'ru-RU' : 'en-US')}`
      : defaultLabel

  /* Four independent requests: totals, balance, cashflow, spending breakdown */
  const summary = useApiQuery(
    () => analyticsApi.getSummary({ startDate, endDate, compare: true }),
    [startDate, endDate],
  )
  const balanceSeries = useApiQuery(
    () => analyticsApi.getTimeseries({ metric: 'balance', groupBy: 'day', startDate, endDate }),
    [startDate, endDate],
  )
  const cashflowSeries = useApiQuery(
    () => analyticsApi.getTimeseries({ metric: 'cashflow', groupBy: 'day', startDate, endDate }),
    [startDate, endDate],
  )
  const expenseStructure = useApiQuery(
    () => analyticsApi.getByCategory({ type: 'expense', startDate, endDate }),
    [startDate, endDate],
  )

  const balancePoints = useMemo(
    () => (balanceSeries.data ? toBalancePoints(balanceSeries.data, locale) : []),
    [balanceSeries.data, locale],
  )
  const cashflowPoints = useMemo(
    () => (cashflowSeries.data ? toCashflowPoints(cashflowSeries.data, locale) : []),
    [cashflowSeries.data, locale],
  )
  const segments = useMemo(
    () => (expenseStructure.data ? toDonutSegments(expenseStructure.data.items, 5) : []),
    [expenseStructure.data],
  )
  const expenseItems = useMemo(
    () => (expenseStructure.data ? expenseStructure.data.items : []),
    [expenseStructure.data],
  )

  const totals = summary.data
  const change = summary.data?.change

  /** Account cards: archived ones are hidden. Excluded-from-statistics accounts are visible
 * in the list but don't affect the numbers — that's what the "excluded" flag is for. */
  const cards = useMemo(
    () => accounts.filter((account) => !account.archived).slice(0, 5),
    [accounts],
  )

  /*
   * "Bank-style" balance: the server returns the balance at the end of the selected period,
   * already converted to the base currency. Summing `account.balance` on the client
   * is wrong: accounts have different currencies, and the number must match the period.
   */
  const balanceOverview = useApiQuery(
    () => accountsApi.getTotalBalance({ startDate, endDate }),
    [startDate, endDate],
  )
  const totalBalance = balanceOverview.data?.total ?? 0


  /** "Spending character": top category, average day and the most expensive day */
  const spendingStats = useMemo(() => {
    const top = segments[0]
    const expenseTotal = totals?.expense ?? 0
    const topShare = top && expenseTotal > 0 ? (Math.abs(top.value) / expenseTotal) * 100 : null

    const start = new Date(startDate).getTime()
    const end = new Date(endDate).getTime()
    const days = Number.isFinite(start) && Number.isFinite(end) && end >= start
      ? Math.round((end - start) / 86_400_000) + 1
      : 1
    const avgPerDay = expenseTotal > 0 ? expenseTotal / Math.max(1, days) : 0

    const busiest = cashflowPoints.reduce(
      (worst, point) => (Math.abs(point.expense) > Math.abs(worst.expense) ? point : worst),
      { label: '', income: 0, expense: 0 },
    )

    // Count transactions by category
    const totalTransactions = expenseItems.reduce((sum, item) => sum + item.transactions_count, 0)
    const avgTransaction = totalTransactions > 0 ? Math.abs(expenseTotal) / totalTransactions : 0
    const categoryCount = expenseItems.length

    // Top 5 categories with shares
    const topCategories = expenseItems.slice(0, 5).map((item) => ({
      name: item.name,
      value: Math.abs(item.total),
      share: expenseTotal > 0 ? (Math.abs(item.total) / Math.abs(expenseTotal)) * 100 : 0,
      transactions: item.transactions_count,
    }))

    return {
      topCategory: top?.name ?? null,
      topShare,
      avgPerDay,
      busiestDay: busiest.expense !== 0 ? busiest.label : null,
      busiestDayValue: Math.abs(busiest.expense),
      totalTransactions,
      avgTransaction,
      categoryCount,
      topCategories,
    }
  }, [segments, totals, cashflowPoints, startDate, endDate, expenseItems])

  /* Period comparison: the same cashflow but for the previous month */
  const previousBounds = monthBounds(monthOffset - 1)
  const previousSeries = useApiQuery(
    () => analyticsApi.getTimeseries({ metric: 'cashflow', groupBy: 'day', startDate: previousBounds.start, endDate: previousBounds.end }),
    [previousBounds.start, previousBounds.end],
  )

  /** Comparison line: match by day number so the periods overlay */
  const comparisonPoints = useMemo(() => {
    const previous = previousSeries.data ? toCashflowPoints(previousSeries.data, locale) : []
    const pick = (point: { income: number; expense: number }) =>
      comparison === 'expense' ? point.expense : comparison === 'income' ? point.income : point.income + point.expense
    const current = cashflowPoints.map(pick)
    const before = previous.map(pick)
    return current.map((value, index) => ({
      label: cashflowPoints[index]?.label ?? String(index + 1),
      value: value - (before[index] ?? 0),
    }))
  }, [cashflowPoints, previousSeries.data, comparison, locale])

  return (
    <AppShell onAddRecord={onAddRecord}>
      {/* Account cards */}
      <section aria-label={t('nav.accounts')} className="mb-4">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
          {cards.map((account) => (
            <AccountCard
              key={account.id}
              account={account}
              onOpen={() => navigate(`/accounts/${account.id}`)}
            />
          ))}
          <button
            type="button"
            onClick={() => setAccountDialogOpen(true)}
            className="flex h-[50px] items-center justify-center gap-1.5 rounded-md border border-dashed border-stroke-strong text-caption text-fg-tertiary transition-colors hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-45 xl:hidden"
          >
            <Plus className="size-3.5" aria-hidden="true" />
            {t('dashboard.addAccount')}
          </button>
        </div>
        {accounts.length === 0 && (
          <button
            type="button"
            onClick={() => setAccountDialogOpen(true)}
            className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-md border border-dashed border-stroke-strong py-3 text-caption text-fg-tertiary transition-colors hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-45"
          >
            <Plus className="size-3.5" aria-hidden="true" />
            {t('dashboard.addAccount')}
          </button>
        )}
      </section>

      {/* Month toolbar */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <PeriodPicker
          label={range ? rangeLabel : defaultLabel}
          range={range}
          onRangeChange={setRange}
          defaultMonth={bounds.month}
          onPrev={() => {
            setRange(undefined)
            setMonthOffset((value) => value - 1)
          }}
          onNext={() => {
            setRange(undefined)
            setMonthOffset((value) => value + 1)
          }}
        />
        <Button
          variant="glass"
          size="sm"
          pill
          className="gap-1.5"
          onClick={() => setAccountDialogOpen(true)}
        >
          <Plus className="size-4" aria-hidden="true" />
          {t('dashboard.addCard')}
        </Button>
      </div>

      {/* Load failure: otherwise zeros in KPIs look like real data */}
      <QueryError
        error={summary.error ?? balanceSeries.error ?? cashflowSeries.error ?? expenseStructure.error}
        className="mb-4"
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Overview: three KPIs + balance line */}
        <Card className="lg:col-span-2">
          <CardHeader
            title={t('dashboard.overview')}
            subtitle={summary.loading ? t('state.loading') : rangeLabel}
            actions={
              <>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon-sm" aria-label={t('dashboard.customize')}>
                      <LayoutGrid className="size-4" aria-hidden="true" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuLabel>{t('dashboard.customize')}</DropdownMenuLabel>
                    {(['balance', 'cashflow', 'expenses'] as const).map((key) => (
                      <DropdownMenuItem
                        key={key}
                        onSelect={(event) => {
                          // The menu closes itself: don't let it reset the selection
                          event.preventDefault()
                          setHiddenKpi((prev) =>
                            prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key],
                          )
                        }}
                      >
                        <span className="mr-1.5 inline-block w-3 text-accent">
                          {hiddenKpi.includes(key) ? '' : '✓'}
                        </span>
                        {t(`dashboard.${key}`)}
                      </DropdownMenuItem>
                    ))}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onSelect={() => navigate('/settings')}>
                      {t('nav.settings')}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon-sm" aria-label={t('common.more')}>
                      <MoreHorizontal className="size-4" aria-hidden="true" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <DropdownMenuItem onSelect={() => navigate('/analytics')}>
                      {t('nav.analytics')}
                    </DropdownMenuItem>
                    <DropdownMenuItem onSelect={() => navigate('/records')}>
                      {t('nav.records')}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            }
          />
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
            {([
              { key: 'balance' as const, label: t('dashboard.balance'), value: totalBalance, currency: baseCurrency },
              { key: 'cashflow' as const, label: t('dashboard.cashflow'), value: totals?.net ?? 0, currency: baseCurrency },
              { key: 'expenses' as const, label: t('dashboard.expenses'), value: -(totals?.expense ?? 0), currency: baseCurrency },
            ]).filter((item) => !hiddenKpi.includes(item.key)).map((item) => (
              <div key={item.label} className="flex flex-col gap-1">
                <span className="text-overline uppercase text-fg-tertiary">{item.label}</span>
                <Amount
                  value={item.value}
                  currency={item.currency}
                  size="sm"
                  tone="neutral"
                />
              </div>
            ))}
          </div>
          {balancePoints.length > 1 ? (
            <LineChart
              className="mt-2"
              points={balancePoints}
              ariaLabel={`${t('dashboard.balance')} ${rangeLabel}`}
              height={140}
            />
          ) : (
            <p className="mt-4 text-caption text-fg-tertiary">
              {balanceSeries.loading ? t('state.loading') : t('state.empty')}
            </p>
          )}
        </Card>

        {/* Period comparison */}
        <Card>
          <CardHeader title={t('dashboard.periodComparison')} subtitle={t('dashboard.vsPrevious')} />
          <div className="mt-3">
            <SegmentedControl
              aria-label={t('dashboard.periodComparison')}
              value={comparison}
              onValueChange={(value) => setComparison(value as typeof comparison)}
              items={[
                { value: 'cashflow', label: t('dashboard.cashflow') },
                { value: 'expense', label: t('dashboard.expenses') },
                { value: 'income', label: t('dashboard.incomes') },
              ]}
            />
          </div>
          {comparisonPoints.length > 1 ? (
            <LineChart
              className="mt-3"
              points={comparisonPoints}
              ariaLabel={t('dashboard.periodComparison')}
              height={150}
            />
          ) : (
            <p className="mt-3 text-caption text-fg-tertiary">
              {previousSeries.loading ? t('state.loading') : t('state.empty')}
            </p>
          )}
        </Card>

        {/* Balance dynamics */}
        <Card>
          <CardHeader
            title={t('dashboard.balanceDynamics')}
            subtitle={t('dashboard.vsPrevious')}
            actions={
              change?.net !== null && change?.net !== undefined ? (
                <TrendBadge value={change.net} />
              ) : undefined
            }
          />
          <Amount value={totalBalance} currency={baseCurrency} size="lg" tone="neutral" className="mt-2" />
          {balancePoints.length > 1 ? (
            <LineChart
              className="mt-2"
              points={balancePoints}
              ariaLabel={t('dashboard.balanceDynamics')}
              height={120}
            />
          ) : (
            <p className="mt-2 text-caption text-fg-tertiary">{t('state.empty')}</p>
          )}
        </Card>

        {/* Cashflow */}
        <Card>
          <CardHeader
            title={t('dashboard.cashflowTitle')}
            subtitle={t('dashboard.vsPrevious')}
            actions={
              change?.income !== null && change?.income !== undefined ? (
                <TrendBadge value={change.income} />
              ) : undefined
            }
          />
          <Amount
            value={totals?.net ?? 0}
            currency={baseCurrency}
            size="lg"
            tone="neutral"
            className="mt-2"
          />
          <div className="mt-3 flex flex-wrap items-center gap-4 text-caption">
            <span className="flex items-center gap-1.5 text-fg-secondary">
              <span className="size-2 rounded-pill bg-positive" aria-hidden="true" />
              {t('dashboard.incomes')}
              <Amount value={totals?.income ?? 0} size="xs" tone="positive" className="ml-1" />
            </span>
            <span className="flex items-center gap-1.5 text-fg-secondary">
              <span className="size-2 rounded-pill bg-negative" aria-hidden="true" />
              {t('dashboard.expenses')}
              <Amount value={-(totals?.expense ?? 0)} size="xs" tone="negative" className="ml-1" />
            </span>
          </div>
          {cashflowPoints.length > 0 ? (
            <BarChart
              className="mt-3"
              points={cashflowPoints}
              ariaLabel={t('dashboard.cashflowTitle')}
              height={120}
            />
          ) : (
            <p className="mt-3 text-caption text-fg-tertiary">{t('state.empty')}</p>
          )}
        </Card>

        {/* Spending breakdown */}
        <Card>
          <CardHeader title={t('dashboard.expenseStructure')} subtitle={rangeLabel} />
          {segments.length > 0 ? (
            <div className="mt-3 flex items-center gap-4">
              <DonutChart
                segments={segments}
                ariaLabel={t('dashboard.expenseStructure')}
                center={
                  <span className="flex flex-col items-center">
                    <Amount value={-(totals?.expense ?? 0)} size="sm" tone="negative" />
                  </span>
                }
                size={132}
                thickness={14}
              />
              <ul className="min-w-0 flex-1 space-y-1.5">
                {segments.map((item) => (
                  <li key={item.name} className="flex items-center gap-2 text-caption">
                    <span
                      className="size-2 shrink-0 rounded-pill"
                      style={{ backgroundColor: item.color }}
                      aria-hidden="true"
                    />
                    <span className="truncate text-fg-secondary">{item.name}</span>
                    <Amount value={-item.value} size="xs" tone="neutral" className="ml-auto" />
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="mt-3 text-caption text-fg-tertiary">
              {expenseStructure.loading ? t('state.loading') : t('state.empty')}
            </p>
          )}
        </Card>

        {/* Premium widget: content depends on the plan */}
        <Card className="lg:col-span-3">
          <div className="flex flex-wrap items-start gap-4">
            <span className="grid size-10 place-items-center rounded-md bg-accent-soft text-accent-on-soft">
              <Sparkles className="size-5" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h2 className="text-headline font-semibold text-fg-primary">
                {t('dashboard.spendingCharacter')}
              </h2>
            </div>
          </div>

            <div className="mt-4 space-y-5">
              {/* Metrics */}
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div className="flex flex-col gap-1">
                  <span className="text-overline uppercase text-fg-tertiary">{t('dashboard.topCategory')}</span>
                  <span className="truncate text-label font-medium text-fg-primary">
                    {spendingStats.topCategory ?? '—'}
                  </span>
                  <span className="text-caption text-fg-tertiary">
                    {spendingStats.topShare === null ? '—' : `${spendingStats.topShare.toFixed(0)}%`}
                  </span>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-overline uppercase text-fg-tertiary">{t('dashboard.avgPerDay')}</span>
                  <Amount value={spendingStats.avgPerDay} currency={baseCurrency} size="sm" tone="neutral" />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-overline uppercase text-fg-tertiary">{t('dashboard.busiestDay')}</span>
                  <span className="truncate text-label font-medium text-fg-primary">
                    {spendingStats.busiestDay ?? '—'}
                  </span>
                  <Amount value={spendingStats.busiestDayValue} currency={baseCurrency} size="sm" tone="negative" />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-overline uppercase text-fg-tertiary">{t('dashboard.totalTransactions')}</span>
                  <span className="text-label font-medium text-fg-primary">
                    {spendingStats.totalTransactions}
                  </span>
                  <span className="text-caption text-fg-tertiary">
                    {t('dashboard.avgTx')}: {spendingStats.avgTransaction > 0 ? spendingStats.avgTransaction.toFixed(2) : '—'} {baseCurrency}
                  </span>
                </div>
              </div>

              {/* Category breakdown */}
              {spendingStats.topCategories.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-caption font-medium text-fg-secondary">
                      {t('dashboard.categoryBreakdown')}
                    </span>
                    <span className="text-caption text-fg-tertiary">
                      {spendingStats.categoryCount} {t('dashboard.categories')}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {spendingStats.topCategories.map((cat, idx) => (
                      <div key={cat.name} className="space-y-1">
                        <div className="flex items-center gap-2 text-caption">
                          <span className="min-w-0 flex-1 truncate text-fg-secondary">
                            {cat.name}
                          </span>
                          <span className="shrink-0 text-fg-tertiary">
                            {cat.transactions} {t('dashboard.tx')}
                          </span>
                          <span className="shrink-0 text-fg-tertiary">
                            {cat.share.toFixed(0)}%
                          </span>
                          <Amount value={-cat.value} size="xs" tone="negative" />
                        </div>
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${cat.share}%`,
                              backgroundColor: `var(--chart-${(idx % 6) + 1})`,
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
        </Card>
      </div>

      <AccountDialog open={accountDialogOpen} onOpenChange={setAccountDialogOpen} account={null} />

    </AppShell>
  )
}
