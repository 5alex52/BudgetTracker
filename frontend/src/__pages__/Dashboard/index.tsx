import { useState } from 'react'
import { Eye, LayoutGrid, MoreHorizontal, Plus, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useI18n } from '@/i18n'
import {
  balanceSeries,
  cashflowSeries,
  dashboardCards,
  expenseStructure,
  periodComparison,
} from '@/__shared__/mock/finance'
import { AppShell } from '@/components/layout/AppShell'
import { AccountCard } from '@/components/data/AccountCard'
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

/** «Обзор»: счёт-карты, навигатор месяца, шесть виджетов из референса. */
export function DashboardPage() {
  const { t, locale } = useI18n()
  const { openCreate: onAddRecord } = useRecordDialog()
  const navigate = useNavigate()
  /* Период: по умолчанию месяц, но можно выбрать произвольный диапазон дат */
  const [range, setRange] = useState<import('react-day-picker').DateRange | undefined>(undefined)
  /** Месяц обзора: стрелки сдвигают его, подпись следует за выбором */
  const [monthOffset, setMonthOffset] = useState(0)
  const [accountDialogOpen, setAccountDialogOpen] = useState(false)
  const [upgradeOpen, setUpgradeOpen] = useState(false)
  /** Срез сравнения периодов: денежный поток / расходы / доходы */
  const [comparison, setComparison] = useState<'cashflow' | 'expense' | 'income'>('cashflow')
  const baseMonth = new Date(2025, 9, 1)
  const shownMonth = new Date(baseMonth.getFullYear(), baseMonth.getMonth() + monthOffset, 1)
  const monthLabel = new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
    month: 'long',
    year: 'numeric',
  }).format(shownMonth)
  const rangeLabel =
    range?.from && range?.to
      ? `${range.from.toLocaleDateString(locale === 'ru' ? 'ru-RU' : 'en-US')} — ${range.to.toLocaleDateString(locale === 'ru' ? 'ru-RU' : 'en-US')}`
      : monthLabel

  return (
    <AppShell onAddRecord={onAddRecord}>
      {/* Счёт-карты */}
      <section aria-label={t('nav.accounts')} className="mb-4">
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">
          {dashboardCards.slice(0, 5).map((account) => (
            <AccountCard key={account.id} account={account} onOpen={() => navigate(`/accounts/${account.id}`)} />
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
      </section>

      {/* Тулбар месяца */}
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <PeriodPicker
          label={range ? rangeLabel : monthLabel}
          range={range}
          onRangeChange={setRange}
          defaultMonth={shownMonth}
          onPrev={() => {
            setRange(undefined)
            setMonthOffset((value) => value - 1)
          }}
          onNext={() => {
            setRange(undefined)
            setMonthOffset((value) => value + 1)
          }}
        />
        <Button variant="glass" size="sm" pill className="gap-1.5" onClick={() => setAccountDialogOpen(true)}>
          <Plus className="size-4" aria-hidden="true" />
          {t('dashboard.addCard')}
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Обзор: три KPI + линия */}
        <Card className="lg:col-span-2">
          <CardHeader
            title={t('dashboard.overview')}
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
                      <DropdownMenuItem key={key}>{t(`dashboard.${key}`)}</DropdownMenuItem>
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
                    <DropdownMenuItem onSelect={() => navigate('/records')}>{t('nav.records')}</DropdownMenuItem>
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
            {[
              { label: t('dashboard.balance'), value: 16059.73 },
              { label: t('dashboard.cashflow'), value: 9937.92 },
              { label: t('dashboard.expenses'), value: -2329.15 },
            ].map((item) => (
              <div key={item.label} className="flex flex-col gap-1">
                <span className="text-overline uppercase text-fg-tertiary">{item.label}</span>
                <Amount value={item.value} size="sm" tone="neutral" hideDecimals />
              </div>
            ))}
          </div>
          <LineChart
            className="mt-2"
            points={balanceSeries.map((point) => ({ label: point.label, value: point.value }))}
            ariaLabel={`${t('dashboard.balance')} ${monthLabel}`}
            height={140}
          />
        </Card>

        {/* Сравнение периодов */}
        <Card>
          <CardHeader title={t('dashboard.periodComparison')} />
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
          <LineChart
            className="mt-3"
            points={periodComparison.map((point) => ({
              label: point.label,
              value:
                comparison === 'cashflow' ? point.cashflow : comparison === 'expense' ? point.expense : point.income,
            }))}
            ariaLabel={t('dashboard.periodComparison')}
            height={150}
          />
        </Card>

        {/* Динамика баланса */}
        <Card>
          <CardHeader
            title={t('dashboard.balanceDynamics')}
            subtitle={t('dashboard.vsPrevious')}
            actions={<TrendBadge value={174} />}
          />
          <Amount value={16059.73} size="lg" tone="neutral" className="mt-2" />
          <LineChart
            className="mt-2"
            points={balanceSeries.map((point) => ({ label: point.label, value: point.value }))}
            ariaLabel={t('dashboard.balanceDynamics')}
            height={120}
          />
        </Card>

        {/* Денежный поток */}
        <Card>
          <CardHeader
            title={t('dashboard.cashflowTitle')}
            subtitle={t('dashboard.vsPrevious')}
            actions={<TrendBadge value={999} />}
          />
          <Amount value={9937.92} size="lg" tone="neutral" className="mt-2" />
          <div className="mt-3 flex flex-wrap items-center gap-4 text-caption">
            <span className="flex items-center gap-1.5 text-fg-secondary">
              <span className="size-2 rounded-pill bg-positive" aria-hidden="true" />
              {t('dashboard.incomes')}
              <Amount value={12267.07} size="xs" tone="positive" className="ml-1" />
            </span>
            <span className="flex items-center gap-1.5 text-fg-secondary">
              <span className="size-2 rounded-pill bg-negative" aria-hidden="true" />
              {t('dashboard.expenses')}
              <Amount value={-2329.15} size="xs" tone="negative" className="ml-1" />
            </span>
          </div>
          <BarChart
            className="mt-3"
            points={cashflowSeries}
            ariaLabel={t('dashboard.cashflowTitle')}
            height={120}
          />
        </Card>

        {/* Структура расходов */}
        <Card>
          <CardHeader title={t('dashboard.expenseStructure')} subtitle={t('dashboard.vsPrevious')} />
          <div className="mt-3 flex items-center gap-4">
            <DonutChart
              segments={expenseStructure}
              ariaLabel={t('dashboard.expenseStructure')}
              center={
                <span className="flex flex-col items-center">
                  <Amount value={-2329.15} size="sm" tone="negative" hideDecimals />
                  <TrendBadge value={69} />
                </span>
              }
              size={132}
              thickness={14}
            />
            <ul className="min-w-0 flex-1 space-y-1.5">
              {expenseStructure.map((item) => (
                <li key={item.name} className="flex items-center gap-2 text-caption">
                  <span
                    className="size-2 shrink-0 rounded-pill"
                    style={{ backgroundColor: item.color }}
                    aria-hidden="true"
                  />
                  <span className="truncate text-fg-secondary">{item.name}</span>
                  <Amount value={item.value} size="xs" tone="neutral" className="ml-auto" />
                </li>
              ))}
            </ul>
          </div>
        </Card>

        {/* Премиум-виджет */}
        <Card className="lg:col-span-3">
          <div className="flex flex-wrap items-center gap-4">
            <span className="grid size-10 place-items-center rounded-md bg-accent-soft text-accent-on-soft">
              <Sparkles className="size-5" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h2 className="text-headline font-semibold text-fg-primary">
                {t('dashboard.spendingCharacter')}
              </h2>
              <p className="text-caption text-fg-secondary">
                {t('dashboard.upgradePremium')} — {t('dashboard.upgradeHint')}
              </p>
            </div>
            <Button variant="primary" size="sm" pill className="ml-auto gap-1.5" onClick={() => setUpgradeOpen(true)}>
              <Eye className="size-4" aria-hidden="true" />
              {t('dashboard.upgrade')}
            </Button>
          </div>
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
