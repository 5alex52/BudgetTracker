import { useMemo, useState } from 'react'
import { Pencil, Plus, Repeat, Trash2 } from 'lucide-react'
import { ApiError, serviceSubsApi } from '@/api'
import type { ServiceSubDto, ServiceSubFrequency } from '@/api/types'
import { useApiQuery } from '@/hooks/useApi'
import { useI18n, type TranslationKey } from '@/i18n'
import { useFinanceStore } from '@/store/finance'
import { ServiceIcon } from '@/components/icons/service-icons'
import { AppShell } from '@/components/layout/AppShell'
import { Amount } from '@/components/data/Amount'
import { ValueBarChart } from '@/components/charts/charts'
import { Button } from '@/components/ui/button'
import { Card, CardHeader } from '@/components/ui/card'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { Field, Input } from '@/components/ui/field'
import { FilterSelect } from '@/components/ui/overlays'
import { Switch } from '@/components/ui/toggles'
import { useToast } from '@/components/ui/toast'

const FREQUENCIES: Array<{ value: ServiceSubFrequency; labelKey: TranslationKey }> = [
  { value: 'monthly', labelKey: 'subs.freqMonthly' },
  { value: 'quarterly', labelKey: 'subs.freqQuarterly' },
  { value: 'yearly', labelKey: 'subs.freqYearly' },
]

/** Сервер знает и daily/weekly — UI предлагает только три периода. */
function normalizeFrequency(value: string): ServiceSubFrequency {
  return value === 'quarterly' || value === 'yearly' ? value : 'monthly'
}

function formatDate(iso: string, locale: 'ru' | 'en') {
  return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(iso))
}

function formatMonth(month: string, locale: 'ru' | 'en') {
  return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', { month: 'short' }).format(
    new Date(`${month}-01T00:00:00`),
  )
}

function todayISO(): string {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

interface PaymentDraft {
  name: string
  price: string
  currency: string
  account: string
  frequency: ServiceSubFrequency
  date: string
}

const EMPTY_DRAFT: PaymentDraft = { name: '', price: '', currency: '', account: '', frequency: 'monthly', date: '' }

function draftFromSub(sub: ServiceSubDto): PaymentDraft {
  return {
    name: sub.name,
    price: String(sub.price),
    currency: sub.currency_id,
    account: sub.account_id === null ? '' : String(sub.account_id),
    frequency: normalizeFrequency(sub.frequency),
    date: sub.started_at.slice(0, 10),
  }
}

/**
 * Форма регулярного платежа: создание и редактирование в одном диалоге.
 * В отличие от подписки, иконки нет, а счёт обязателен — иначе списывать некуда.
 */
function PaymentDialog({
  open,
  sub,
  onClose,
  onSaved,
}: {
  open: boolean
  sub: ServiceSubDto | null
  onClose: () => void
  onSaved: () => void
}) {
  const { t } = useI18n()
  const { toast } = useToast()
  const currencyCodes = useFinanceStore((state) => state.currencyCodes)
  const accounts = useFinanceStore((state) => state.accounts)
  const [draft, setDraft] = useState<PaymentDraft>(EMPTY_DRAFT)
  const [pending, setPending] = useState(false)
  // Повторное открытие диалога может быть с другим платежом — синхронизируем черновик.
  const [lastKey, setLastKey] = useState<string | null>(null)
  const key = open ? String(sub?.id ?? 'new') : null
  if (key !== lastKey) {
    setLastKey(key)
    if (key !== null) {
      setDraft(
        sub
          ? draftFromSub(sub)
          : { ...EMPTY_DRAFT, currency: currencyCodes()[0] ?? 'USD', date: todayISO() },
      )
    }
  }

  const priceValue = Number(draft.price.replace(',', '.'))
  const canSave =
    draft.name.trim() !== '' &&
    Number.isFinite(priceValue) &&
    priceValue > 0 &&
    draft.account !== '' &&
    draft.date !== ''

  const save = async () => {
    if (!canSave) return
    setPending(true)
    try {
      const payload = {
        name: draft.name.trim(),
        price: priceValue,
        currency_id: draft.currency,
        started_at: `${draft.date}T00:00:00`,
        account_id: Number(draft.account),
        frequency: draft.frequency,
      }
      if (sub) {
        await serviceSubsApi.updateServiceSub(sub.id, payload)
      } else {
        await serviceSubsApi.createServiceSub(payload)
      }
      toast({ title: t('autoRules.saved'), tone: 'success' })
      onSaved()
      onClose()
    } catch (caught) {
      toast({
        title: t('subs.saveFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    } finally {
      setPending(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent
        title={t(sub ? 'autoRules.edit' : 'autoRules.new')}
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={onClose}>
              {t('common.cancel')}
            </Button>
            <Button size="sm" disabled={!canSave} loading={pending} onClick={() => void save()}>
              {t('common.save')}
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t('autoRules.name')}>
              <Input
                value={draft.name}
                placeholder={t('autoRules.namePlaceholder')}
                onChange={(event) => setDraft((prev) => ({ ...prev, name: event.target.value }))}
              />
            </Field>
            <Field label={t('subs.price')}>
              <Input
                inputMode="decimal"
                value={draft.price}
                onChange={(event) => setDraft((prev) => ({ ...prev, price: event.target.value }))}
              />
            </Field>
            <Field label={t('subs.currency')}>
              <FilterSelect
                ariaLabel={t('subs.currency')}
                value={draft.currency}
                onValueChange={(value) => setDraft((prev) => ({ ...prev, currency: value }))}
                options={currencyCodes().map((code) => ({ value: code, label: code }))}
              />
            </Field>
            <Field label={t('subs.frequency')}>
              <FilterSelect
                ariaLabel={t('subs.frequency')}
                value={draft.frequency}
                onValueChange={(value) =>
                  setDraft((prev) => ({ ...prev, frequency: value as ServiceSubFrequency }))
                }
                options={FREQUENCIES.map((entry) => ({ value: entry.value, label: t(entry.labelKey) }))}
              />
            </Field>
            <Field label={t('subs.start')}>
              <Input
                type="date"
                value={draft.date}
                onChange={(event) => setDraft((prev) => ({ ...prev, date: event.target.value }))}
              />
            </Field>
          </div>

          <Field label={t('subs.account')} hint={t('autoRules.accountHint')}>
            <FilterSelect
              ariaLabel={t('subs.account')}
              value={draft.account}
              onValueChange={(value) => setDraft((prev) => ({ ...prev, account: value }))}
              options={accounts
                .filter((account) => !account.archived)
                .map((account) => ({ value: String(account.id), label: account.name }))}
            />
          </Field>
        </div>
      </DialogContent>
    </Dialog>
  )
}

/**
 * Автоправила: подписки и регулярные платежи с привязанным счётом списывают
 * себя сами. При открытии страницы создаются пропущенные списания, периодичность
 * и пауза правятся прямо в строке, а новый платёж (например, по кредиту)
 * добавляется без иконки сервиса.
 */
export function AutoRulesPage() {
  const { t, locale } = useI18n()
  const { toast } = useToast()
  const accountById = useFinanceStore((state) => state.accountById)
  /* Сначала доводим расписание: наступившие даты списания превращаются в записи. */
  const list = useApiQuery(async () => {
    await serviceSubsApi.collectServiceSubs().catch(() => undefined)
    return serviceSubsApi.listServiceSubs()
  }, [])
  const summary = useApiQuery(() => serviceSubsApi.getChargesSummary(6), [list.data])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<ServiceSubDto | null>(null)
  const [removing, setRemoving] = useState<ServiceSubDto | null>(null)
  const [busy, setBusy] = useState(false)

  const rules = useMemo(
    () => (list.data?.items ?? []).filter((sub) => sub.account_id !== null),
    [list.data],
  )
  const chartPoints = useMemo(
    () =>
      (summary.data ?? []).map((point) => ({
        label: formatMonth(point.month, locale),
        value: point.total,
      })),
    [summary.data, locale],
  )

  const refresh = () => {
    list.reload()
  }

  const openCreate = () => {
    setEditing(null)
    setDialogOpen(true)
  }
  const openEdit = (sub: ServiceSubDto) => {
    setEditing(sub)
    setDialogOpen(true)
  }

  const patch = async (sub: ServiceSubDto, payload: { frequency?: ServiceSubFrequency; rule_active?: boolean }, successKey: TranslationKey) => {
    try {
      await serviceSubsApi.updateServiceSub(sub.id, payload)
      toast({ title: t(successKey), tone: 'success' })
      refresh()
    } catch (caught) {
      toast({
        title: t('subs.saveFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    }
  }

  const remove = async () => {
    if (!removing) return
    setBusy(true)
    try {
      await serviceSubsApi.deleteServiceSub(removing.id)
      toast({ title: t('autoRules.deleted'), tone: 'success' })
      setRemoving(null)
      refresh()
    } catch (caught) {
      toast({
        title: t('subs.deleteFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <AppShell
      header={
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-title font-semibold tracking-snug text-fg-primary">{t('autoRules.title')}</h1>
            <p className="mt-1 text-caption text-fg-tertiary">{t('autoRules.subtitle')}</p>
          </div>
          <Button size="sm" className="gap-1.5" onClick={openCreate}>
            <Plus className="size-4" aria-hidden="true" />
            {t('autoRules.add')}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Итог в базовой валюте */}
        <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
          <div>
            <p className="text-caption text-fg-tertiary">{t('subs.total')}</p>
            {list.data ? (
              <Amount value={list.data.total_base} currency={list.data.base_currency} size="lg" tone="neutral" />
            ) : (
              <p className="text-title font-semibold text-fg-primary">—</p>
            )}
          </div>
          <p className="text-caption text-fg-tertiary">{t('subs.count', { count: rules.length })}</p>
        </Card>

        {/* График списаний по расписанию */}
        {chartPoints.length > 0 && (
          <Card className="p-4">
            <CardHeader title={t('autoRules.chartTitle')} subtitle={t('subs.chartSubtitle')} />
            <ValueBarChart className="mt-3" points={chartPoints} ariaLabel={t('subs.chargesSeries')} height={140} />
          </Card>
        )}

        {list.error ? (
          <Card className="flex flex-col items-center gap-2 p-6 text-center">
            <p className="text-label text-fg-secondary">{t('state.error')}</p>
            <Button variant="subtle" size="sm" onClick={refresh}>
              {t('state.retry')}
            </Button>
          </Card>
        ) : list.loading && !list.data ? (
          <p className="text-label text-fg-tertiary">{t('state.loading')}</p>
        ) : rules.length === 0 ? (
          <Card className="flex flex-col items-center gap-3 p-8 text-center">
            <p className="text-label text-fg-secondary">{t('autoRules.empty')}</p>
            <Button size="sm" className="gap-1.5" onClick={openCreate}>
              <Plus className="size-4" aria-hidden="true" />
              {t('autoRules.add')}
            </Button>
          </Card>
        ) : (
          <div className="space-y-3">
            {rules.map((sub) => (
              <Card key={sub.id} className="p-4">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="grid size-10 shrink-0 place-items-center overflow-hidden rounded-md bg-surface-2 text-fg-secondary">
                    {sub.icon ? (
                      <ServiceIcon name={sub.icon} size={24} />
                    ) : (
                      <span className="text-label font-semibold">{sub.name[0].toUpperCase()}</span>
                    )}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-label font-medium text-fg-primary">{sub.name}</p>
                    <p className="mt-0.5 truncate text-caption text-fg-tertiary">
                      {accountById(sub.account_id ?? '')?.name ?? '—'} · {t('subs.start')}:{' '}
                      {formatDate(sub.started_at, locale)}
                    </p>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <Amount value={sub.price} currency={sub.currency_id} size="md" tone="neutral" />
                    {list.data && sub.currency_id !== list.data.base_currency && (
                      <span className="text-caption text-fg-tertiary">
                        ≈ <Amount value={sub.price_base} currency={list.data.base_currency} size="sm" tone="neutral" />
                      </span>
                    )}
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Button variant="ghost" size="icon-sm" aria-label={t('common.edit')} onClick={() => openEdit(sub)}>
                      <Pencil className="size-4" aria-hidden="true" />
                    </Button>
                    <Button variant="ghost" size="icon-sm" aria-label={t('common.delete')} onClick={() => setRemoving(sub)}>
                      <Trash2 className="size-4" aria-hidden="true" />
                    </Button>
                  </div>
                </div>

                {/* Правило списания: периодичность, дата и пауза — прямо в строке */}
                <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-md border border-stroke-subtle bg-surface-2/60 px-3 py-2">
                  <div className="flex min-w-0 items-center gap-2.5">
                    <span
                      className={`grid size-8 shrink-0 place-items-center rounded-md ${
                        sub.rule_active === true
                          ? 'bg-accent-soft text-accent-on-soft'
                          : 'bg-surface-1 text-fg-tertiary'
                      }`}
                    >
                      <Repeat className="size-4" aria-hidden="true" />
                    </span>
                    <div className="min-w-0">
                      <p className="text-label font-medium text-fg-primary">{t('subs.autoRule')}</p>
                      <p className="truncate text-caption text-fg-tertiary">
                        {sub.next_payment_date
                          ? `${t('subs.nextCharge')}: ${formatDate(sub.next_payment_date, locale)}`
                          : '—'}
                      </p>
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-wrap items-center gap-3">
                    <FilterSelect
                      ariaLabel={t('subs.frequency')}
                      value={normalizeFrequency(sub.frequency)}
                      onValueChange={(value) =>
                        void patch(sub, { frequency: value as ServiceSubFrequency }, 'autoRules.saved')
                      }
                      options={FREQUENCIES.map((entry) => ({ value: entry.value, label: t(entry.labelKey) }))}
                      className="w-40"
                    />
                    <span
                      className={`text-caption font-medium ${
                        sub.rule_active === true ? 'text-accent' : 'text-fg-tertiary'
                      }`}
                    >
                      {sub.rule_active === true ? t('subs.ruleOn') : t('subs.ruleOff')}
                    </span>
                    <Switch
                      checked={sub.rule_active === true}
                      onCheckedChange={(active) =>
                        void patch(sub, { rule_active: active }, active ? 'subs.ruleResumed' : 'subs.rulePaused')
                      }
                      aria-label={t('subs.autoRule')}
                    />
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>

      <PaymentDialog open={dialogOpen} sub={editing} onClose={() => setDialogOpen(false)} onSaved={refresh} />

      <Dialog open={removing !== null} onOpenChange={(next) => !next && setRemoving(null)}>
        <DialogContent
          title={t('autoRules.deleteTitle')}
          description={removing ? `${removing.name} — ${t('subs.deleteHint')}` : undefined}
          footer={
            <>
              <Button variant="ghost" size="sm" onClick={() => setRemoving(null)}>
                {t('common.cancel')}
              </Button>
              <Button size="sm" loading={busy} onClick={() => void remove()}>
                {t('common.delete')}
              </Button>
            </>
          }
        />
      </Dialog>
    </AppShell>
  )
}
