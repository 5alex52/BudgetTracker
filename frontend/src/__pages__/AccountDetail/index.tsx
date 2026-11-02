import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ChevronLeft, MoreHorizontal, Plus, Trash2 } from 'lucide-react'
import { useI18n, type TranslationKey } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import type { AccountKind, RecordItem } from '@/__shared__/types/models'
import { ApiError } from '@/api'
import { analyticsApi } from '@/api'
import { useApiQuery } from '@/hooks/useApi'
import { toBalancePoints } from '@/api/mappers'
import { useFinanceStore } from '@/store/finance'
import { transactionsApi } from '@/api'
import { toRecordItem } from '@/api/mappers'
import { AccountDialog } from '@/components/accounts/AccountDialog'
import { ExportMenu } from '@/components/data/ExportMenu'
import { useToast } from '@/components/ui/toast'
import { useRecordDialog } from '@/components/records/RecordDialogContext'
import { AppShell } from '@/components/layout/AppShell'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Amount } from '@/components/data/Amount'
import { Checkbox, SegmentedControl } from '@/components/ui/toggles'
import { LineChart } from '@/components/charts/charts'
import { CategoryIcon } from '@/__shared__/utils/category-icon'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/overlays'
import { Dialog, DialogContent } from '@/components/ui/dialogs'

const KIND_LABEL: Record<AccountKind, TranslationKey> = {
  checking: 'accounts.type.checking',
  savings: 'accounts.type.savings',
  cash: 'accounts.type.cash',
  credit_card: 'accounts.type.credit_card',
  investment: 'accounts.type.investment',
}

/**
 * «Детали счёта».
 *
 * Баланс, обороты за период и график берутся из `/accounts/{id}/summary` и
 * `/analytics/timeseries` (остаток по всем счетам — отдельная метрика сервиса),
 * записи — из общего стора с фильтром по счёту.
 */
export function AccountDetailPage() {
  const { openCreate: onAddRecord, openEdit: onEditRecord } = useRecordDialog()
  const navigate = useNavigate()
  const { toast } = useToast()
  const { t, locale } = useI18n()
  const { accountId } = useParams()

  const accounts = useFinanceStore((state) => state.accounts)
  const deleteAccount = useFinanceStore((state) => state.deleteAccount)

  const [dialogOpen, setDialogOpen] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [confirmDedupe, setConfirmDedupe] = useState(false)
  const [tab, setTab] = useState<'balance' | 'records'>('balance')
  const [selected, setSelected] = useState<string[]>([])

  const account = accounts.find((item) => item.id === String(accountId))

  /* Записи именно этого счёта: страница открывается и по прямой ссылке,
     поэтому список грузим здесь, а не берём из общего стора «Записей» */
  const recordsQuery = useApiQuery(
    () =>
      transactionsApi
        .listTransactions({ account_ids: [Number(accountId)], sort: 'date_desc', limit: 100 })
        .then((result) => result.items.map((dto) => toRecordItem(dto, { accounts: new Map() }))),
    [accountId],
  )

  /* Обороты счёта и график остатка: два независимых запроса под вкладкой «Баланс» */
  const summary = useApiQuery(
    () => (accountId ? analyticsApi.getByAccount() : Promise.resolve({ items: [], total: 0 })),
    [accountId],
  )
  const balanceSeries = useApiQuery(
    () => analyticsApi.getTimeseries({ metric: 'balance', groupBy: 'day' }),
    [accountId],
  )

  const accountSummary = summary.data?.items.find((item) => String(item.account_id) === String(accountId))
  const points = balanceSeries.data ? toBalancePoints(balanceSeries.data, locale) : []

  const accountRecords = useMemo(() => recordsQuery.data ?? [], [recordsQuery.data])

  const groups = useMemo(() => {
    const byDate = new Map<string, RecordItem[]>()
    accountRecords.forEach((item) => {
      byDate.set(item.date, [...(byDate.get(item.date) ?? []), item])
    })
    return [...byDate.entries()]
  }, [accountRecords])

  if (!account) {
    return (
      <AppShell context={t('nav.accounts')}>
        <Card>
          <p className="text-body text-fg-secondary">{t('account.notFound')}</p>
          <Link to="/accounts" className="mt-3 inline-block text-label text-accent hover:underline">
            {t('nav.accounts')}
          </Link>
        </Card>
      </AppShell>
    )
  }

  const remove = async () => {
    try {
      await deleteAccount(account.id)
      setConfirmDelete(false)
      toast({ title: t('accounts.deleted'), description: account.name, tone: 'info' })
      navigate('/accounts')
    } catch (caught) {
      toast({
        title: t('accounts.deleteFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    }
  }

  const removeRecordById = async (id: string) => {
    try {
      await transactionsApi.deleteTransaction(Number(id))
      await recordsQuery.reload()
      toast({ title: t('state.deleted'), tone: 'info' })
    } catch {
      toast({ title: t('records.deleteFailed'), tone: 'error' })
    }
  }

  return (
    <AppShell
      context={t('account.detail')}
      header={
        <div className="space-y-3">
          <Link
            to="/accounts"
            className="inline-flex items-center gap-1 text-caption text-fg-secondary hover:text-fg-primary"
          >
            <ChevronLeft className="size-3.5" aria-hidden="true" />
            {t('account.detail')}
          </Link>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-title font-semibold tracking-snug text-fg-primary">{account.name}</h1>
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="subtle" size="sm" onClick={() => setDialogOpen(true)}>
                {t('common.edit')}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="text-[var(--negative)]"
                onClick={() => setConfirmDelete(true)}
              >
                <Trash2 className="size-4" aria-hidden="true" />
                {t('common.delete')}
              </Button>
              <Button size="sm" onClick={onAddRecord} className="gap-1.5">
                <Plus className="size-4" aria-hidden="true" />
                {t('nav.addRecord')}
              </Button>
            </div>
          </div>
        </div>
      }
    >
      <div className="w-full space-y-4">
        <Card>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <dl className="grid gap-3 sm:grid-cols-2">
              <div>
                <dt className="text-caption uppercase tracking-wide text-fg-tertiary">{t('account.name')}</dt>
                <dd className="mt-0.5 text-label font-medium text-fg-primary">{account.name}</dd>
              </div>
              <div>
                <dt className="text-caption uppercase tracking-wide text-fg-tertiary">{t('account.type')}</dt>
                <dd className="mt-0.5 flex items-center gap-2 text-label font-medium text-fg-primary">
                  <span
                    className="size-2 rounded-pill"
                    style={{ backgroundColor: account.tint }}
                    aria-hidden="true"
                  />
                  {t(KIND_LABEL[account.kind])}
                </dd>
              </div>
            </dl>

            <SegmentedControl
              aria-label={t('account.detail')}
              value={tab}
              onValueChange={(value) => setTab(value as 'balance' | 'records')}
              items={[
                { value: 'balance', label: t('account.tab.balance') },
                { value: 'records', label: t('account.tab.records') },
              ]}
            />
          </div>

          <div className="mt-4 flex flex-wrap items-end justify-between gap-3 border-t border-stroke-subtle pt-4">
            <div>
              <p className="text-caption uppercase tracking-wide text-fg-tertiary">{t('dashboard.balance')}</p>
              <Amount value={account.balance} currency={account.currency} size="lg" className="mt-1" />
            </div>
            {accountSummary && (
              <p className="flex flex-wrap items-center gap-3 text-caption text-fg-tertiary">
                <span className="flex items-center gap-1.5">
                  <span className="size-2 rounded-pill bg-positive" aria-hidden="true" />
                  {t('dashboard.incomes')}
                  <Amount value={accountSummary.income} currency={account.currency} size="xs" tone="positive" />
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="size-2 rounded-pill bg-negative" aria-hidden="true" />
                  {t('dashboard.expenses')}
                  <Amount value={-accountSummary.expense} currency={account.currency} size="xs" tone="negative" />
                </span>
                <span>
                  {t('records.found', { count: accountSummary.transactions_count })}
                </span>
              </p>
            )}
          </div>

          {tab === 'balance' && (
            <>
              {points.length > 1 ? (
                <LineChart
                  points={points}
                  height={200}
                  ariaLabel={`${t('dashboard.balance')} — ${account.name}`}
                  className="mt-4"
                />
              ) : (
                <p className="mt-4 text-caption text-fg-tertiary">
                  {balanceSeries.loading ? t('state.loading') : t('state.empty')}
                </p>
              )}
            </>
          )}
        </Card>

        {tab === 'records' && (
          <Card className="overflow-hidden p-0">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stroke-subtle px-4 py-2.5">
              <div className="flex items-center gap-2">
                <Checkbox
                  checked={selected.length > 0 && selected.length === accountRecords.length}
                  onCheckedChange={(next) => setSelected(next ? accountRecords.map((item) => item.id) : [])}
                  label={t('records.selectAll')}
                />
                <p className="text-label text-fg-secondary">
                  {t('records.found', { count: accountRecords.length })}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <ExportMenu items={accountRecords} serverFilters={{ account_ids: [Number(accountId)] }} />
                <Button variant="ghost" size="sm" onClick={() => setConfirmDedupe(true)}>
                  {t('account.dedupe')}
                </Button>
              </div>
            </div>

            {accountRecords.length === 0 && (
              <p className="px-4 py-8 text-center text-label text-fg-tertiary">{t('records.empty')}</p>
            )}

            {groups.map(([date, items]) => {
              const dayTotal = items.reduce((sum, item) => sum + item.amount, 0)
              return (
                <div key={date}>
                  <div className="flex items-center justify-between gap-2 border-t border-stroke-subtle bg-surface-2/40 px-4 py-1.5">
                    <span className="text-caption font-medium text-fg-secondary">
                      {new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
                        day: 'numeric',
                        month: 'long',
                        year: 'numeric',
                      }).format(new Date(`${date}T00:00:00`))}
                    </span>
                    <Amount value={dayTotal} currency={account.currency} size="xs" />
                  </div>
                  <ul>
                    {items.map((item, index) => (
                      <li
                        key={item.id}
                        className={cn(
                          'flex items-center gap-3 px-4 py-2.5 transition-colors duration-fast hover:bg-surface-2/70',
                          index > 0 && 'border-t border-stroke-subtle',
                        )}
                      >
                        <span className="hidden sm:block">
                          <Checkbox
                            checked={selected.includes(item.id)}
                            onCheckedChange={(next) =>
                              setSelected((prev) =>
                                next ? [...prev, item.id] : prev.filter((id) => id !== item.id),
                              )
                            }
                            aria-label={item.category}
                          />
                        </span>
                        <span
                          className="grid size-8 shrink-0 place-items-center rounded-pill"
                          style={{ backgroundColor: `${item.categoryColor}22`, color: item.categoryColor }}
                        >
                          <CategoryIcon name={item.categoryIcon} className="size-4" />
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-label font-medium text-fg-primary">{item.category}</p>
                          <p className="truncate text-caption text-fg-tertiary">
                            {item.date} · {item.time}
                          </p>
                        </div>
                        <Amount value={item.amount} currency={item.currency} size="sm" className="shrink-0" />
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon-sm" aria-label={t('records.rowMenu')}>
                              <MoreHorizontal className="size-4" aria-hidden="true" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onSelect={() => onEditRecord?.(item)}>
                              {t('common.edit')}
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              className="text-[var(--negative)]"
                              onSelect={() => void removeRecordById(item.id)}
                            >
                              {t('common.delete')}
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </li>
                    ))}
                  </ul>
                </div>
              )
            })}
          </Card>
        )}
      </div>

      <AccountDialog open={dialogOpen} onOpenChange={setDialogOpen} account={account} />

      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent
          title={t('accounts.deleteConfirm')}
          description={account.name}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => setConfirmDelete(false)}>
                {t('common.cancel')}
              </Button>
              <Button
                className="bg-[var(--negative)] hover:bg-[var(--negative)]/90"
                onClick={() => void remove()}
              >
                {t('common.delete')}
              </Button>
            </div>
          }
        >
          <p className="text-body text-fg-secondary">{t('accounts.deleteWarning')}</p>
        </DialogContent>
      </Dialog>

      <Dialog open={confirmDedupe} onOpenChange={setConfirmDedupe}>
        <DialogContent
          title={t('accounts.dedupeConfirm')}
          description={account.name}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => setConfirmDedupe(false)}>
                {t('common.cancel')}
              </Button>
              <Button
                onClick={() => {
                  setConfirmDedupe(false)
                  toast({ title: t('account.dedupe'), description: t('accounts.dedupeDone'), tone: 'success' })
                }}
              >
                {t('account.dedupe')}
              </Button>
            </div>
          }
        >
          <p className="text-body text-fg-secondary">{t('accounts.dedupeWarning')}</p>
        </DialogContent>
      </Dialog>
    </AppShell>
  )
}
