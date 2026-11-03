import { useEffect, useMemo, useState } from 'react'
import { Archive, Eye, Lock, Sparkles, Trash2 } from 'lucide-react'
import { useI18n, type TranslationKey } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import type { Account, AccountKind } from '@/__shared__/types/models'
import { ACCOUNT_TINTS } from '@/api/mappers'
import { useFinanceStore } from '@/store/finance'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { SegmentedControl, Switch } from '@/components/ui/toggles'
import { FilterSelect } from '@/components/ui/overlays'
import { useToast } from '@/components/ui/toast'
import { ApiError } from '@/api'
import { useEntitlements } from '@/hooks/useEntitlements'
import { useNavigate } from 'react-router-dom'

/** Типы счетов, которые поддерживает сервис. */
const ACCOUNT_KINDS: AccountKind[] = ['checking', 'savings', 'cash', 'credit_card', 'investment']

const KIND_LABEL_KEY: Record<AccountKind, TranslationKey> = {
  checking: 'accounts.type.checking',
  savings: 'accounts.type.savings',
  cash: 'accounts.type.cash',
  credit_card: 'accounts.type.credit_card',
  investment: 'accounts.type.investment',
}

/** Пустой счёт для формы создания. */
const emptyAccount = (currency: string): Account => ({
  id: '',
  name: '',
  kind: 'checking',
  balance: 0,
  currency,
  tint: ACCOUNT_TINTS[4],
})

/**
 * Форма счёта: создание и редактирование.
 *
 * Название, тип, валюта и остаток уходят на сервер; маркер цвета живёт только
 * на клиенте (в API такого поля нет) и запоминается в localStorage. Валюта после
 * создания не меняется: остаток уже посчитан в ней, а конвертацию баланса сервис
 * не делает — поле блокируется, чтобы не переписать историю.
 */
export function AccountDialog({
  open,
  onOpenChange,
  account,
  onDeleted,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** null — создание нового счёта */
  account?: Account | null
  onDeleted?: () => void
}) {
  const { t } = useI18n()
  const { toast } = useToast()
  const navigate = useNavigate()
  const entitlements = useEntitlements().data
  // Пока права тарифа не загружены, считаем тариф бесплатным: иначе на долю
  // секунды интерфейс предлагал бы платную валюту.
  const multiCurrency = entitlements?.multi_currency === true
  const baseCurrency = useFinanceStore((state) => state.baseCurrency)
  const currencyCodes = useFinanceStore((state) => state.currencyCodes)
  const createAccount = useFinanceStore((state) => state.createAccount)
  const updateAccount = useFinanceStore((state) => state.updateAccount)
  const deleteAccount = useFinanceStore((state) => state.deleteAccount)

  const editing = Boolean(account?.id)
  // Заблокированный счёт доступен только для чтения: архивировать и исключать
  // из статистики всё ещё можно, остальные поля — после возобновления подписки.
  const locked = Boolean(account?.locked)
  const [draft, setDraft] = useState<Account>(account ?? emptyAccount(baseCurrency))
  const [touched, setTouched] = useState(false)
  const [pending, setPending] = useState(false)

  useEffect(() => {
    if (open) {
      setDraft(account ?? emptyAccount(baseCurrency))
      setTouched(false)
    }
  }, [open, account, baseCurrency])

  const nameInvalid = touched && !draft.name.trim()
  const balanceValue = Number(String(draft.balance).replace(',', '.'))

  /**
   * Валюта счёта. Без мультивалютности список сужается до базовой: если счёт
   * уже открыт в другой валюте, оставляем её единственным (заблокированным)
   * вариантом, чтобы форма не подменила валюту при сохранении.
   */
  const currencyOptions = useMemo(() => {
    const all = currencyCodes().map((code) => ({ value: code, label: code }))
    if (multiCurrency) return all
    const locked = draft.currency
    if (locked && locked !== baseCurrency) return [{ value: locked, label: locked }]
    return [{ value: baseCurrency, label: baseCurrency }]
  }, [currencyCodes, multiCurrency, draft.currency, baseCurrency])

  const foreignCurrencyLocked =
    !multiCurrency && Boolean(draft.currency) && draft.currency !== baseCurrency

  const save = async () => {
    setTouched(true)
    if (!draft.name.trim()) return
    setPending(true)
    try {
      const payload = {
        name: draft.name.trim(),
        type: draft.kind,
        currency_id: draft.currency,
        balance: Number.isFinite(balanceValue) ? balanceValue : 0,
        is_archived: Boolean(draft.archived),
        is_excluded: Boolean(draft.excluded),
      }
      if (editing && account) {
        // Заблокированный счёт принимает только архив/исключение: остальные
        // поля сервер отклонит, поэтому и не отправляем их.
        await updateAccount(
          account.id,
          locked
            ? { is_archived: payload.is_archived, is_excluded: payload.is_excluded }
            : payload,
          draft.tint,
        )
        toast({ title: t('state.saved'), description: draft.name, tone: 'success' })
      } else {
        await createAccount(payload, draft.tint)
        toast({
          title: t('accounts.created'),
          description: `${draft.name} · ${payload.balance} ${draft.currency}`,
          tone: 'success',
        })
      }
      onOpenChange(false)
    } catch (caught) {
      toast({
        title: editing ? t('accounts.updateFailed') : t('accounts.createFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    } finally {
      setPending(false)
    }
  }

  const destroy = async () => {
    if (!draft.id) return
    setPending(true)
    try {
      await deleteAccount(draft.id)
      toast({ title: t('accounts.deleted'), description: draft.name, tone: 'info' })
      onOpenChange(false)
      onDeleted?.()
    } catch (caught) {
      toast({
        title: t('accounts.deleteFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    } finally {
      setPending(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        title={editing ? t('accounts.editTitle') : t('accounts.addTitle')}
        description={editing ? draft.name : t('accounts.subtitle')}
        className="[--dialog-w:min(620px,calc(100vw-2rem))]"
        footer={
          <div className="flex flex-wrap items-center justify-between gap-2">
            {editing ? (
              <Button
                variant="ghost"
                className="gap-1.5 text-[var(--negative)]"
                onClick={() => void destroy()}
                disabled={pending}
              >
                <Trash2 className="size-4" aria-hidden="true" />
                {t('common.delete')}
              </Button>
            ) : (
              <span />
            )}
            <div className="flex gap-2">
              <Button variant="subtle" onClick={() => onOpenChange(false)}>
                {t('common.cancel')}
              </Button>
              <Button onClick={() => void save()} disabled={!draft.name.trim() || pending}>
                {pending ? t('state.saving') : editing ? t('common.save') : t('common.add')}
              </Button>
            </div>
          </div>
        }
      >
        <div className="space-y-4">
          {locked && (
            <div className="flex items-start gap-2 rounded-md border-l-2 border-l-[var(--accent)] bg-surface-2/60 px-3 py-2">
              <Lock className="mt-0.5 size-4 shrink-0 text-accent" aria-hidden="true" />
              <p className="text-caption text-fg-secondary">
                {draft.lockReason === 'subscription_required_currency'
                  ? t('accounts.lockedCurrency')
                  : t('accounts.lockedLimit')}
              </p>
            </div>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t('account.name')} error={nameInvalid ? t('recordForm.required') : undefined}>
              <Input
                value={draft.name}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                onBlur={() => setTouched(true)}
                invalid={nameInvalid}
                placeholder={t('account.name')}
                disabled={locked}
                autoFocus={!locked}
              />
            </Field>

            <Field
              label={t('accounts.currency')}
              hint={
                foreignCurrencyLocked
                  ? t('accounts.currencyBaseOnly')
                  : editing
                    ? t('accounts.currencyLocked')
                    : undefined
              }
            >
              {multiCurrency ? (
                <FilterSelect
                  ariaLabel={t('accounts.currency')}
                  value={draft.currency}
                  disabled={locked}
                  onValueChange={(value) => setDraft({ ...draft, currency: value })}
                  options={currencyOptions}
                />
              ) : (
                <div className="flex flex-wrap items-center gap-2">
                  <FilterSelect
                    ariaLabel={t('accounts.currency')}
                    value={draft.currency}
                    disabled
                    options={currencyOptions}
                  />
                  <Button
                    variant="subtle"
                    size="sm"
                    className="gap-1.5"
                    onClick={() => navigate('/settings/payments')}
                  >
                    <Sparkles className="size-3.5" aria-hidden="true" />
                    {t('accounts.currencyUpgradeCta')}
                  </Button>
                </div>
              )}
            </Field>
          </div>

          <div>
            <p className="mb-2 text-label font-medium text-fg-primary">{t('account.type')}</p>
            <SegmentedControl
              aria-label={t('account.type')}
              value={draft.kind}
              onValueChange={(value) => setDraft({ ...draft, kind: value as AccountKind })}
              items={ACCOUNT_KINDS.map((kind) => ({
                value: kind,
                label: t(KIND_LABEL_KEY[kind]),
                disabled: locked,
              }))}
            />
          </div>

          <Field
            label={`${t('accounts.balance')} (${draft.currency})`}
            hint={editing ? t('accounts.balanceHint') : undefined}
          >
            <Input
              value={String(draft.balance).replace('.', ',')}
              onChange={(event) =>
                setDraft({ ...draft, balance: event.target.value as unknown as number })
              }
              inputMode="decimal"
              placeholder="0,00"
              disabled={editing}
            />
          </Field>

          <div>
            <p className="mb-2 text-label font-medium text-fg-primary">{t('accounts.color')}</p>
            <div className="flex flex-wrap gap-2">
              {ACCOUNT_TINTS.map((tint) => (
                <button
                  key={tint}
                  type="button"
                  onClick={() => setDraft({ ...draft, tint })}
                  aria-label={tint}
                  aria-pressed={draft.tint === tint}
                  className={cn(
                    'size-6 rounded-pill border-2 transition-transform',
                    draft.tint === tint
                      ? 'scale-110 border-fg-primary'
                      : 'border-transparent hover:scale-105',
                  )}
                  style={{ backgroundColor: tint }}
                />
              ))}
            </div>
          </div>

          <div className="space-y-2 rounded-md bg-surface-2/60 p-3">
            <Switch
              checked={Boolean(draft.excluded)}
              onCheckedChange={(next) => setDraft({ ...draft, excluded: next })}
              label={
                <span className="flex items-center gap-1.5">
                  <Eye className="size-3.5 text-fg-tertiary" aria-hidden="true" />
                  {t('accounts.exclude')}
                </span>
              }
            />
            <Switch
              checked={Boolean(draft.archived)}
              onCheckedChange={(next) => setDraft({ ...draft, archived: next })}
              label={
                <span className="flex items-center gap-1.5">
                  <Archive className="size-3.5 text-fg-tertiary" aria-hidden="true" />
                  {t('accounts.archived')}
                </span>
              }
            />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
