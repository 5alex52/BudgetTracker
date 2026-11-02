import { useMemo, useState } from 'react'
import { Eye, LayoutGrid, MoreHorizontal, Plus, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useI18n } from '@/i18n'
import { accountsApi, analyticsApi } from '@/api'
import { toBalancePoints, toCashflowPoints, toDonutSegments } from '@/api/mappers'
import { useApiQuery } from '@/hooks/useApi'
import { useEntitlements } from '@/hooks/useEntitlements'
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
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/overlays'

/** Границы базового периода: день, неделя или месяц со сдвигом назад. */
function periodBounds(period: 'day' | 'week' | 'month', offset: number) {
  const iso = (date: Date) => date.toISOString().slice(0, 10)
  const now = new Date()

  if (period === 'day') {
    const day = new Date(now.getFullYear(), now.getMonth(), now.getDate() + offset)
    return { start: iso(day), end: iso(day), month: day }
  }
  if (period === 'week') {
    // Неделя начинается с понедельника: getDay() отдаёт 0 для воскресенья
    const shift = (now.getDay() + 6) % 7
    const monday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - shift + offset * 7)
    const sunday = new Date(monday.getFullYear(), monday.getMonth(), monday.getDate() + 6)
    return { start: iso(monday), end: iso(sunday), month: monday }
  }
  return monthBounds(offset)
}

/** Границы месяца по смещению от текущего: 0 — этот месяц, −1 — прошлый. */
function monthBounds(offset: number) {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth() + offset, 1)
  const end = new Date(now.getFullYear(), now.getMonth() + offset + 1, 0)
  const iso = (date: Date) => date.toISOString().slice(0, 10)
  return { start: iso(start), end: iso(end), month: start }
}

/**
 * «Обзор».
 *
 * Все KPI, графики и структура расходов считаются на сервере:
 * `/analytics/summary` отдаёт итоги и сравнение с предыдущим периодом,
 * `/analytics/timeseries` — линии и столбцы, `/analytics/by-category` — доли.
 * Клиент только раскладывает ответы по виджетам.
 */
export function DashboardPage() {
  const { t, locale } = useI18n()
  const { openCreate: onAddRecord } = useRecordDialog()
  const navigate = useNavigate()

  const accounts = useFinanceStore((state) => state.accounts)
  const baseCurrency = useFinanceStore((state) => state.baseCurrency)

  /* Период: по умолчанию текущий месяц, можно выбрать произвольный диапазон */
  const [range, setRange] = useState<import('react-day-picker').DateRange | undefined>(undefined)
  const [monthOffset, setMonthOffset] = useState(0)
  const [accountDialogOpen, setAccountDialogOpen] = useState(false)
  const [upgradeOpen, setUpgradeOpen] = useState(false)
  const [comparison, setComparison] = useState<'cashflow' | 'expense' | 'income'>('cashflow')
  /** Какие KPI показывать: меню «Настроить» действительно переключает плитки */
  const [hiddenKpi, setHiddenKpi] = useState<Array<'balance' | 'cashflow' | 'expenses'>>([])

  /* Базовый период из настроек: день, неделя или месяц */
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

  /* Четыре независимых запроса: итоги, баланс, денежный поток, структура расходов */
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

  const totals = summary.data
  const change = summary.data?.change

  /** Карточки счетов: исключённые из статистики и архивные не показываем */
  const cards = useMemo(
    () => accounts.filter((account) => !account.excluded && !account.archived).slice(0, 5),
    [accounts],
  )

  /*
   * Баланс «как в банке»: сервер отдаёт остаток на конец выбранного периода,
   * уже пересчитанный в базовую валюту. Складывать `account.balance` на клиенте
   * нельзя: у счетов разные валюты, а цифра должна соответствовать периоду.
   */
  const balanceOverview = useApiQuery(
    () => accountsApi.getTotalBalance({ startDate, endDate }),
    [startDate, endDate],
  )
  const totalBalance = balanceOverview.data?.total ?? 0

  /* Тариф: от него зависит, показывать премиум-виджет или кнопку апгрейда */
  const entitlementsQuery = useEntitlements()
  const entitlements = entitlementsQuery.data
  const isPremium = entitlements?.advanced_analytics === true

  /** «Характер расходов»: главная категория, средний день и самый затратный день */
  const premiumStats = useMemo(() => {
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

    return {
      topCategory: top?.name ?? null,
      topShare,
      avgPerDay,
      busiestDay: busiest.expense !== 0 ? busiest.label : null,
      busiestDayValue: Math.abs(busiest.expense),
    }
  }, [segments, totals, cashflowPoints, startDate, endDate])

  /* Сравнение периодов: тот же денежный поток, но за предыдущий месяц */
  const previousBounds = monthBounds(monthOffset - 1)
  const previousSeries = useApiQuery(
    () => analyticsApi.getTimeseries({ metric: 'cashflow', groupBy: 'day', startDate: previousBounds.start, endDate: previousBounds.end }),
    [previousBounds.start, previousBounds.end],
  )

  /** Линия сравнения: сопоставляем по номеру дня, чтобы периоды наложились */
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
      {/* Счёт-карты */}
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
            className="flex h-[50px] items-center justify-center gap-1.5 rounded-md border border-dashed border-stroke-strong text-caption text-fg-tertiary transition-colors hover:border-accent hover:text-accent xl:hidden"
          >
            <Plus className="size-3.5" aria-hidden="true" />
            {t('dashboard.addAccount')}
          </button>
        </div>
        {accounts.length === 0 && (
          <button
            type="button"
            onClick={() => setAccountDialogOpen(true)}
            className="mt-2 flex w-full items-center justify-center gap-1.5 rounded-md border border-dashed border-stroke-strong py-3 text-caption text-fg-tertiary transition-colors hover:border-accent hover:text-accent"
          >
            <Plus className="size-3.5" aria-hidden="true" />
            {t('dashboard.addAccount')}
          </button>
        )}
      </section>

      {/* Тулбар месяца */}
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

      {/* Сбой загрузки: иначе нули в KPI выглядят как настоящие данные */}
      <QueryError
        error={summary.error ?? balanceSeries.error ?? cashflowSeries.error ?? expenseStructure.error}
        className="mb-4"
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Обзор: три KPI + линия остатка */}
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
                          // Меню закрывается само: не даём ему сбросить выбор
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
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onSelect={() => setUpgradeOpen(true)}>
                      {t('dashboard.upgrade')}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            }
          />
          <div className="mt-4 grid grid-cols-3 gap-3">
            {([
              { key: 'balance' as const, label: t('dashboard.balance'), value: totalBalance, currency: baseCurrency },
              { key: 'cashflow' as const, label: t('dashboard.cashflow'), value: totals?.net ?? 0, currency: '' },
              { key: 'expenses' as const, label: t('dashboard.expenses'), value: -(totals?.expense ?? 0), currency: '' },
            ]).filter((item) => !hiddenKpi.includes(item.key)).map((item) => (
              <div key={item.label} className="flex flex-col gap-1">
                <span className="text-overline uppercase text-fg-tertiary">{item.label}</span>
                <Amount
                  value={item.value}
                  currency={item.currency || undefined}
                  size="sm"
                  tone="neutral"
                  hideDecimals
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

        {/* Сравнение периодов */}
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

        {/* Динамика баланса */}
        <Card>
          <CardHeader
            title={t('dashboard.balanceDynamics')}
            subtitle={t('dashboard.vsPrevious')}
            actions={
              change?.net !== null && change?.net !== undefined ? (
                <TrendBadge value={Math.round(change.net)} />
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

        {/* Денежный поток */}
        <Card>
          <CardHeader
            title={t('dashboard.cashflowTitle')}
            subtitle={t('dashboard.vsPrevious')}
            actions={
              change?.income !== null && change?.income !== undefined ? (
                <TrendBadge value={Math.round(change.income)} />
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

        {/* Структура расходов */}
        <Card>
          <CardHeader title={t('dashboard.expenseStructure')} subtitle={rangeLabel} />
          {segments.length > 0 ? (
            <div className="mt-3 flex items-center gap-4">
              <DonutChart
                segments={segments}
                ariaLabel={t('dashboard.expenseStructure')}
                center={
                  <span className="flex flex-col items-center">
                    <Amount value={-(totals?.expense ?? 0)} size="sm" tone="negative" hideDecimals />
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

        {/* Премиум-виджет: содержимое зависит от тарифа */}
        <Card className="lg:col-span-3">
          <div className="flex flex-wrap items-start gap-4">
            <span className="grid size-10 place-items-center rounded-md bg-accent-soft text-accent-on-soft">
              <Sparkles className="size-5" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h2 className="text-headline font-semibold text-fg-primary">
                {t('dashboard.spendingCharacter')}
              </h2>
              <p className="text-caption text-fg-secondary">
                {isPremium
                  ? `${t('dashboard.premiumPlan')}: ${entitlements?.plan_name ?? ''}`
                  : `${t('dashboard.upgradePremium')} — ${t('dashboard.upgradeHint')}`}
              </p>
            </div>
            {!isPremium && (
              <Button
                variant="primary"
                size="sm"
                pill
                className="ml-auto gap-1.5"
                onClick={() => setUpgradeOpen(true)}
              >
                <Eye className="size-4" aria-hidden="true" />
                {t('dashboard.upgrade')}
              </Button>
            )}
          </div>

          {isPremium && (
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div className="flex flex-col gap-1">
                <span className="text-overline uppercase text-fg-tertiary">{t('dashboard.topCategory')}</span>
                <span className="truncate text-label font-medium text-fg-primary">
                  {premiumStats.topCategory ?? '—'}
                </span>
                <span className="text-caption text-fg-tertiary">
                  {premiumStats.topShare === null ? '—' : `${premiumStats.topShare.toFixed(0)}%`}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-overline uppercase text-fg-tertiary">{t('dashboard.avgPerDay')}</span>
                <Amount value={premiumStats.avgPerDay} currency={baseCurrency} size="sm" tone="neutral" />
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-overline uppercase text-fg-tertiary">{t('dashboard.busiestDay')}</span>
                <span className="truncate text-label font-medium text-fg-primary">
                  {premiumStats.busiestDay ?? '—'}
                </span>
                <Amount value={premiumStats.busiestDayValue} currency={baseCurrency} size="sm" tone="negative" />
              </div>
            </div>
          )}
        </Card>
      </div>

      <AccountDialog open={accountDialogOpen} onOpenChange={setAccountDialogOpen} account={null} />

      <Dialog open={upgradeOpen} onOpenChange={setUpgradeOpen}>
        <DialogContent
          title={t('dashboard.upgrade')}
          description={t('dashboard.upgradeHint')}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => setUpgradeOpen(false)}>
                {t('common.cancel')}
              </Button>
              <Button
                onClick={() => {
                  setUpgradeOpen(false)
                  navigate('/settings/payments')
                }}
              >
                {t('payments.changePlan')}
              </Button>
            </div>
          }
        >
          <ul className="space-y-2 text-label text-fg-secondary">
            {[t('payments.feature1'), t('payments.feature2'), t('payments.feature3')].map((feature) => (
              <li key={feature} className="flex items-center gap-2">
                <Sparkles className="size-3.5 text-accent" aria-hidden="true" />
                {feature}
              </li>
            ))}
          </ul>
        </DialogContent>
      </Dialog>
    </AppShell>
  )
}
