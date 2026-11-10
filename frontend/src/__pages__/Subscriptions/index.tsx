import { useMemo, useRef, useState } from 'react'
import { Pencil, Plus, Trash2, Upload, X } from 'lucide-react'
import { ApiError, serviceSubsApi } from '@/api'
import type { ServiceSubCreatePayload, ServiceSubDto, ServiceSubUpdatePayload } from '@/api/types'
import { useApiQuery } from '@/hooks/useApi'
import { useI18n } from '@/i18n'
import { useFinanceStore } from '@/store/finance'
import { ServiceIcon, SERVICE_ICONS } from '@/components/icons/service-icons'
import { AppShell } from '@/components/layout/AppShell'
import { Amount } from '@/components/data/Amount'
import { ValueBarChart } from '@/components/charts/charts'
import { Button } from '@/components/ui/button'
import { Card, CardHeader } from '@/components/ui/card'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { Field, Input } from '@/components/ui/field'
import { FilterSelect } from '@/components/ui/overlays'
import { useToast } from '@/components/ui/toast'

const MAX_ICON_BYTES = 48 * 1024

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

function toPayload(draft: SubDraft): ServiceSubCreatePayload {
  return {
    name: draft.name.trim(),
    icon: draft.icon || undefined,
    price: Number(draft.price.replace(',', '.')),
    currency_id: draft.currency,
    started_at: `${draft.date}T00:00:00`,
    account_id: draft.account === '' ? null : Number(draft.account),
  }
}

interface SubDraft {
  name: string
  price: string
  currency: string
  date: string
  icon: string
  account: string
}

const EMPTY_DRAFT: SubDraft = { name: '', price: '', currency: '', date: '', icon: '', account: '' }

function draftFromSub(sub: ServiceSubDto): SubDraft {
  return {
    name: sub.name,
    price: String(sub.price),
    currency: sub.currency_id,
    date: sub.started_at.slice(0, 10),
    icon: sub.icon ?? '',
    account: sub.account_id === null ? '' : String(sub.account_id),
  }
}

/** Форма одной подписки: создание и редактирование в одном диалоге. */
function SubDialog({
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
  const fileInput = useRef<HTMLInputElement>(null)
  const [draft, setDraft] = useState<SubDraft>(EMPTY_DRAFT)
  const [pending, setPending] = useState(false)
  // Повторное открытие диалога может быть с другой подпиской — синхронизируем черновик.
  const [lastKey, setLastKey] = useState<string | null>(null)
  const key = open ? String(sub?.id ?? 'new') : null
  if (key !== lastKey) {
    setLastKey(key)
    if (key !== null) setDraft(sub ? draftFromSub(sub) : { ...EMPTY_DRAFT, currency: currencyCodes()[0] ?? 'USD' })
  }

  const priceValue = Number(draft.price.replace(',', '.'))
  const canSave = draft.name.trim() !== '' && Number.isFinite(priceValue) && priceValue > 0 && draft.date !== ''

  const pickFile = (file: File | undefined) => {
    if (!file) return
    if (file.size > MAX_ICON_BYTES) {
      toast({ title: t('subs.iconTooLarge'), tone: 'error' })
      return
    }
    const reader = new FileReader()
    reader.onload = () => setDraft((prev) => ({ ...prev, icon: String(reader.result ?? '') }))
    reader.readAsDataURL(file)
  }

  const save = async () => {
    if (!canSave) return
    setPending(true)
    try {
      const payload = toPayload(draft)
      if (sub) {
        await serviceSubsApi.updateServiceSub(sub.id, payload as ServiceSubUpdatePayload)
      } else {
        await serviceSubsApi.createServiceSub(payload)
      }
      toast({ title: t('subs.saved'), tone: 'success' })
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
        title={t(sub ? 'subs.edit' : 'subs.new')}
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
          {/* Иконка: популярные сервисы или своё изображение */}
          <Field label={t('subs.icon')}>
            <div className="flex flex-wrap items-center gap-2">
              <span className="grid size-10 shrink-0 place-items-center overflow-hidden rounded-md bg-surface-2 text-fg-secondary">
                {draft.icon ? (
                  <ServiceIcon name={draft.icon} size={24} />
                ) : (
                  <span className="text-label font-semibold">{(draft.name || '?')[0].toUpperCase()}</span>
                )}
              </span>
              <div className="flex flex-wrap gap-1.5">
                {SERVICE_ICONS.map((icon) => (
                  <button
                    key={icon.key}
                    type="button"
                    title={icon.label}
                    aria-label={icon.label}
                    onClick={() => setDraft((prev) => ({ ...prev, icon: prev.icon === icon.key ? '' : icon.key }))}
                    className={
                      'grid size-8 place-items-center rounded-md border transition-colors ' +
                      (draft.icon === icon.key
                        ? 'border-accent bg-accent-soft text-accent'
                        : 'border-stroke-subtle bg-surface-1 text-fg-secondary hover:text-fg-primary')
                    }
                  >
                    <ServiceIcon name={icon.key} size={18} />
                  </button>
                ))}
              </div>
              <input
                ref={fileInput}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={(event) => pickFile(event.target.files?.[0])}
              />
              <Button variant="glass" size="sm" className="gap-1.5" onClick={() => fileInput.current?.click()}>
                <Upload className="size-4" aria-hidden="true" />
                {t('subs.iconUpload')}
              </Button>
              {draft.icon && (
                <Button variant="ghost" size="icon-sm" aria-label={t('subs.iconNone')} onClick={() => setDraft((prev) => ({ ...prev, icon: '' }))}>
                  <X className="size-4" aria-hidden="true" />
                </Button>
              )}
            </div>
          </Field>

          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t('subs.name')}>
              <Input value={draft.name} onChange={(event) => setDraft((prev) => ({ ...prev, name: event.target.value }))} />
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
            <Field label={t('subs.start')}>
              <Input
                type="date"
                value={draft.date}
                onChange={(event) => setDraft((prev) => ({ ...prev, date: event.target.value }))}
              />
            </Field>
          </div>

          <Field label={t('subs.account')} hint={t('subs.accountHint')}>
            <FilterSelect
              ariaLabel={t('subs.account')}
              value={draft.account}
              onValueChange={(value) => setDraft((prev) => ({ ...prev, account: value }))}
              options={[
                { value: '', label: t('subs.accountNone') },
                ...accounts
                  .filter((account) => !account.archived)
                  .map((account) => ({ value: String(account.id), label: account.name })),
              ]}
            />
          </Field>
        </div>
      </DialogContent>
    </Dialog>
  )
}

/**
 * Учёт платных подписок: цена в своей валюте, итог — в базовой.
 * Подписка с привязанным счётом списывает себя автоматически: при открытии
 * страницы создаются пропущенные записи-списания, а график показывает суммы.
 */
export function SubscriptionsPage() {
  const { t, locale } = useI18n()
  const { toast } = useToast()
  /* При каждой загрузке сначала доводим расписание: наступившие даты списания
     превращаются в записи, затем берём свежий список. */
  const list = useApiQuery(async () => {
    await serviceSubsApi.collectServiceSubs().catch(() => undefined)
    return serviceSubsApi.listServiceSubs()
  }, [])
  const summary = useApiQuery(() => serviceSubsApi.getChargesSummary(6), [list.data])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<ServiceSubDto | null>(null)
  const [removing, setRemoving] = useState<ServiceSubDto | null>(null)
  const [busy, setBusy] = useState(false)

  const items = useMemo(() => list.data?.items ?? [], [list.data])
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

  const remove = async () => {
    if (!removing) return
    setBusy(true)
    try {
      await serviceSubsApi.deleteServiceSub(removing.id)
      toast({ title: t('subs.deleted'), tone: 'success' })
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
            <h1 className="text-title font-semibold tracking-snug text-fg-primary">{t('subs.title')}</h1>
            <p className="mt-1 text-caption text-fg-tertiary">{t('subs.subtitle')}</p>
          </div>
          <Button size="sm" className="gap-1.5" onClick={openCreate}>
            <Plus className="size-4" aria-hidden="true" />
            {t('subs.add')}
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
          <p className="text-caption text-fg-tertiary">{t('subs.count', { count: items.length })}</p>
        </Card>

        {/* График списаний по подпискам */}
        {chartPoints.length > 0 && (
          <Card className="p-4">
            <CardHeader title={t('subs.chartTitle')} subtitle={t('subs.chartSubtitle')} />
            <ValueBarChart className="mt-3" points={chartPoints} ariaLabel={t('subs.chargesSeries')} height={140} />
          </Card>
        )}

        {/* Мои подписки */}
        {list.error ? (
          <Card className="flex flex-col items-center gap-2 p-6 text-center">
            <p className="text-label text-fg-secondary">{t('state.error')}</p>
            <Button variant="subtle" size="sm" onClick={refresh}>
              {t('state.retry')}
            </Button>
          </Card>
        ) : list.loading && !list.data ? (
          <p className="text-label text-fg-tertiary">{t('state.loading')}</p>
        ) : items.length === 0 ? (
          <Card className="flex flex-col items-center gap-3 p-8 text-center">
            <p className="text-label text-fg-secondary">{t('subs.empty')}</p>
            <Button size="sm" className="gap-1.5" onClick={openCreate}>
              <Plus className="size-4" aria-hidden="true" />
              {t('subs.add')}
            </Button>
          </Card>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {items.map((sub) => (
              <Card key={sub.id} className="p-4">
                <div className="flex items-start gap-3">
                  <span className="grid size-10 shrink-0 place-items-center overflow-hidden rounded-md bg-surface-2 text-fg-secondary">
                    {sub.icon ? <ServiceIcon name={sub.icon} size={24} /> : sub.name[0].toUpperCase()}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-label font-medium text-fg-primary">{sub.name}</p>
                    <p className="mt-0.5 text-caption text-fg-tertiary">
                      {t('subs.start')}: {formatDate(sub.started_at, locale)}
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={t('common.edit')}
                      onClick={() => openEdit(sub)}
                    >
                      <Pencil className="size-4" aria-hidden="true" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={t('common.delete')}
                      onClick={() => setRemoving(sub)}
                    >
                      <Trash2 className="size-4" aria-hidden="true" />
                    </Button>
                  </div>
                </div>
                <div className="mt-3 flex items-baseline justify-between gap-2">
                  <Amount value={sub.price} currency={sub.currency_id} size="md" tone="neutral" />
                  {list.data && sub.currency_id !== list.data.base_currency && (
                    <span className="text-caption text-fg-tertiary">
                      ≈ <Amount value={sub.price_base} currency={list.data.base_currency} size="sm" tone="neutral" />
                    </span>
                  )}
                </div>
                {(sub.next_payment_date !== null || sub.charges.length > 0) && (
                  <div className="mt-2 space-y-1 border-t border-stroke-subtle pt-2 text-caption text-fg-tertiary">
                    {sub.next_payment_date && (
                      <p>
                        {t('subs.nextCharge')}: {formatDate(sub.next_payment_date, locale)}
                      </p>
                    )}
                    {sub.charges.slice(0, 3).map((charge) => (
                      <p key={charge.id} className="flex items-center justify-between gap-2">
                        <span>{formatDate(charge.date, locale)}</span>
                        <Amount value={charge.amount} currency={charge.currency_id} size="xs" tone="negative" />
                      </p>
                    ))}
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>

      <SubDialog open={dialogOpen} sub={editing} onClose={() => setDialogOpen(false)} onSaved={refresh} />

      <Dialog open={removing !== null} onOpenChange={(next) => !next && setRemoving(null)}>
        <DialogContent
          title={t('subs.deleteTitle')}
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
