import { useEffect, useState } from 'react'
import { Archive, Eye, Lock, Trash2 } from 'lucide-react'
import { useI18n } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import type { Account } from '@/__shared__/mock/finance'
import {
  ACCOUNT_CURRENCIES,
  ACCOUNT_KINDS,
  ACCOUNT_TINTS,
  KIND_LABEL_KEY,
  emptyAccount,
  useAccountsStore,
} from '@/store/accounts'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { SegmentedControl, Switch } from '@/components/ui/toggles'
import { FilterSelect } from '@/components/ui/overlays'
import { useToast } from '@/components/ui/toast'

/**
 * Форма счёта: создание и редактирование.
 *
 * Поля повторяют то, что есть в референсе на плитках и в деталях счёта:
 * название, тип, валюта, начальный баланс и цветовой маркер. Дополнительно —
 * три состояния, которые в референсе показаны только иконками в списке:
 * «исключить из статистики», «архив», «только чтение».
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
  const { upsert, remove, nextId } = useAccountsStore()

  const editing = Boolean(account?.id)
  const [draft, setDraft] = useState<Account>(account ?? emptyAccount())
  const [touched, setTouched] = useState(false)

  useEffect(() => {
    if (open) {
      setDraft(account ?? emptyAccount())
      setTouched(false)
    }
  }, [open, account])

  const nameInvalid = touched && !draft.name.trim()

  const save = () => {
    setTouched(true)
    if (!draft.name.trim()) return
    const next: Account = {
      ...draft,
      id: draft.id || nextId(draft.name),
      balance: Number(String(draft.balance).replace(',', '.')) || 0,
    }
    upsert(next)
    toast({
      title: editing ? t('common.save') : t('accounts.created'),
      description: `${next.name} · ${next.balance} ${next.currency}`,
      tone: 'success',
    })
    onOpenChange(false)
  }

  const destroy = () => {
    if (!draft.id) return
    remove(draft.id)
    toast({ title: t('accounts.deleted'), description: draft.name, tone: 'info' })
    onOpenChange(false)
    onDeleted?.()
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
              <Button variant="ghost" className="gap-1.5 text-[var(--negative)]" onClick={destroy}>
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
              <Button onClick={save} disabled={!draft.name.trim()}>
                {editing ? t('common.save') : t('common.add')}
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
                autoFocus
              />
            </Field>

            <Field label={t('accounts.currency')}>
              <FilterSelect
                ariaLabel={t('accounts.currency')}
                value={draft.currency}
                onValueChange={(value) => setDraft({ ...draft, currency: value as Account['currency'] })}
                options={ACCOUNT_CURRENCIES.map((code) => ({ value: code, label: code }))}
              />
            </Field>
          </div>

          <div>
            <p className="mb-2 text-label font-medium text-fg-primary">{t('account.type')}</p>
            <SegmentedControl
              aria-label={t('account.type')}
              value={draft.kind}
              onValueChange={(value) => setDraft({ ...draft, kind: value as Account['kind'] })}
              items={ACCOUNT_KINDS.map((kind) => ({ value: kind, label: t(KIND_LABEL_KEY[kind]) }))}
            />
          </div>

          <Field
            label={`${t('accounts.balance')} (${draft.currency})`}
            hint={editing ? t('accounts.balanceHint') : undefined}
          >
            <Input
              value={String(draft.balance).replace('.', ',')}
              onChange={(event) => setDraft({ ...draft, balance: event.target.value as unknown as number })}
              inputMode="decimal"
              placeholder="0,00"
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
                    draft.tint === tint ? 'scale-110 border-fg-primary' : 'border-transparent hover:scale-105',
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
            <Switch
              checked={Boolean(draft.locked)}
              onCheckedChange={(next) => setDraft({ ...draft, locked: next })}
              label={
                <span className="flex items-center gap-1.5">
                  <Lock className="size-3.5 text-fg-tertiary" aria-hidden="true" />
                  {t('accounts.locked')}
                </span>
              }
            />
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
