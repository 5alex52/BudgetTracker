import { useEffect, useMemo, useState } from 'react'
import { Archive, Eye, Trash2 } from 'lucide-react'
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

/** Account types supported by the service. */
const ACCOUNT_KINDS: AccountKind[] = ['checking', 'savings', 'cash', 'credit_card', 'investment']

const KIND_LABEL_KEY: Record<AccountKind, TranslationKey> = {
  checking: 'accounts.type.checking',
  savings: 'accounts.type.savings',
  cash: 'accounts.type.cash',
  credit_card: 'accounts.type.credit_card',
  investment: 'accounts.type.investment',
}

/** Empty account for the create form. */
const emptyAccount = (currency: string): Account => ({
  id: '',
  name: '',
  kind: 'checking',
  balance: 0,
  currency,
  tint: ACCOUNT_TINTS[4],
})

/**
 * Account form: create and edit.
 *
 * Name, type, currency and balance go to the server; the color marker lives only
 * on the client (the API has no such field) and is remembered in localStorage.
 * The currency can't change after creation: the balance is already computed in it,
 * and the service doesn't convert balances — the field is locked so history isn't rewritten.
 */
export function AccountDialog({
  open,
  onOpenChange,
  account,
  onDeleted,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** null — creating a new account */
  account?: Account | null
  onDeleted?: () => void
}) {
  const { t } = useI18n()
  const { toast } = useToast()
  const baseCurrency = useFinanceStore((state) => state.baseCurrency)
  const currencyCodes = useFinanceStore((state) => state.currencyCodes)
  const createAccount = useFinanceStore((state) => state.createAccount)
  const updateAccount = useFinanceStore((state) => state.updateAccount)
  const deleteAccount = useFinanceStore((state) => state.deleteAccount)

  const editing = Boolean(account?.id)
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

  /** Currency options: the whole catalog. */
  const currencyOptions = useMemo(
    () => currencyCodes().map((code) => ({ value: code, label: code })),
    [currencyCodes],
  )

  const save = async () => {
    setTouched(true)
    if (!draft.name.trim()) return
    setPending(true)
    try {
      const shared = {
        name: draft.name.trim(),
        is_archived: Boolean(draft.archived),
        is_excluded: Boolean(draft.excluded),
      }
      const balance = Number.isFinite(balanceValue) ? balanceValue : 0
      if (editing && account) {
        // crypto account: the server won't let type/currency/balance be edited — they live on the Crypto page
        const payload = draft.crypto
          ? shared
          : { ...shared, type: draft.kind, currency_id: draft.currency, balance }
        await updateAccount(account.id, payload, draft.tint)
        toast({ title: t('state.saved'), description: draft.name, tone: 'success' })
      } else {
        await createAccount({ ...shared, type: draft.kind, currency_id: draft.currency, balance }, draft.tint)
        toast({
          title: t('accounts.created'),
          description: `${draft.name} · ${balance} ${draft.currency}`,
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
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label={t('account.name')} error={nameInvalid ? t('recordForm.required') : undefined}>
              <Input
                value={draft.name}
                onChange={(event) => setDraft({ ...draft, name: event.target.value })}
                onBlur={() => setTouched(true)}
                invalid={nameInvalid}
                placeholder={t('account.name')}
              />
            </Field>

            <Field label={t('accounts.currency')}>
              <FilterSelect
                ariaLabel={t('accounts.currency')}
                value={draft.currency}
                onValueChange={(value) => setDraft({ ...draft, currency: value })}
                options={currencyOptions}
                disabled={draft.crypto}
              />
            </Field>
          </div>

          {draft.crypto && (
            <p className="text-caption text-fg-tertiary">{t('accounts.cryptoHint')}</p>
          )}

          <div>
            <p className="mb-2 text-label font-medium text-fg-primary">{t('account.type')}</p>
            <SegmentedControl
              aria-label={t('account.type')}
              value={draft.kind}
              onValueChange={(value) => setDraft({ ...draft, kind: value as AccountKind })}
              items={ACCOUNT_KINDS.map((kind) => ({
                value: kind,
                label: t(KIND_LABEL_KEY[kind]),
                disabled: draft.crypto,
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
