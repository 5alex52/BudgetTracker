import { useEffect, useMemo, useState } from 'react'
import { CalendarClock, Tags } from 'lucide-react'
import { useI18n } from '@/i18n'
import type { RecordItem } from '@/__shared__/types/models'
import type { TransactionTypeValue } from '@/api/types'
import { ApiError } from '@/api'
import { useFinanceStore } from '@/store/finance'
import { useRecordsStore } from '@/store/records'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { Button } from '@/components/ui/button'
import { Field, Input, Textarea } from '@/components/ui/field'
import { SegmentedControl, Switch } from '@/components/ui/toggles'
import { FilterSelect } from '@/components/ui/overlays'
import { useToast } from '@/components/ui/toast'
import { CategoryIcon } from '@/__shared__/utils/category-icon'
import { cn } from '@/__shared__/utils/cn'
import { toLocalDateISO } from '@/__shared__/utils/format'

/** Amount parsing: accept "12,50", "12.50" and space thousand separators. */
function parseAmount(value: string): number | null {
  const normalized = value.replace(/\s/g, '').replace(',', '.')
  const parsed = Number(normalized)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null
}

/** Form date and time → ISO without a timezone (the server stores "naive" time). */
function toIso(date: string, time: string): string {
  return `${date}T${time || '00:00'}:00`
}

/**
 * "Add record" — the two-column glass modal from the reference.
 *
 * Sends the record to the server: auto-categorization rules, account balance and tags
 * are computed by the backend. The "payment type", "payer" and "confirmed" fields from the mockup
 * were dropped: the data model has no such fields, there'd be nowhere to store them.
 * A transfer has no category: the form asks for the destination account, and the server
 * substitutes a system category and converts currencies at personal rates.
 */
export function AddRecordDialog({
  open,
  onOpenChange,
  record,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** If passed — the modal works in record edit mode */
  record?: RecordItem | null
}) {
  const editing = Boolean(record)
  const { t } = useI18n()
  const { toast } = useToast()

  const accounts = useFinanceStore((state) => state.accounts)
  const categories = useFinanceStore((state) => state.categories)
  const tags = useFinanceStore((state) => state.tags)
  const createTemplate = useFinanceStore((state) => state.createTemplate)
  const createRecord = useRecordsStore((state) => state.create)
  const updateRecord = useRecordsStore((state) => state.update)

  const [type, setType] = useState<TransactionTypeValue>('expense')
  const [amount, setAmount] = useState('')
  const [accountId, setAccountId] = useState('')
  const [toAccountId, setToAccountId] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [note, setNote] = useState('')
  const [date, setDate] = useState(() => toLocalDateISO(new Date()))
  const [time, setTime] = useState(() =>
    new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }),
  )
  const [tagIds, setTagIds] = useState<number[]>([])
  const [makeTemplate, setMakeTemplate] = useState(false)
  const [touched, setTouched] = useState(false)
  const [pending, setPending] = useState(false)

  const isTransfer = type === 'transfer'

  /* Categories for the current record type: expense and income don't mix */
  const availableCategories = useMemo(
    () =>
      isTransfer
        ? []
        : categories.filter((category) => category.type === (type === 'income' ? 'income' : 'expense')),
    [categories, type, isTransfer],
  )

  /**
   * Flat "parent → children" list: group headers in the dropdown were removed
   * on request; nesting reads via indent and a color dot.
   */
  const categoryOptions = useMemo(() => {
    const parents = availableCategories.filter((category) => category.parentId === null)
    return parents.flatMap((parent) => [
      { value: String(parent.id), label: parent.name, dotColor: parent.color },
      ...availableCategories
        .filter((category) => category.parentId === parent.id)
        .map((child) => ({ value: String(child.id), label: child.name, indent: true, dotColor: child.color })),
    ])
  }, [availableCategories])

  const formAccounts = useMemo(
    () => accounts.filter((item) => !item.archived && !item.crypto),
    [accounts],
  )

  const account = accounts.find((item) => item.id === accountId)
  const currency = account?.currency ?? 'BYN'

  useEffect(() => {
    if (!open) return
    if (record) {
      setType(record.type)
      setAmount(String(Math.abs(record.amount)).replace('.', ','))
      setAccountId(record.accountId)
      setToAccountId(record.transferAccountId ?? '')
      setCategoryId(String(record.categoryId))
      setNote(record.note ?? '')
      setDate(record.date)
      setTime(record.time)
      setTagIds(record.tags.map((tag) => tag.id))
      setMakeTemplate(false)
      setTouched(false)
      return
    }

    setType('expense')
    setAmount('')
    setAccountId(formAccounts[0]?.id ?? '')
    setToAccountId('')
    setCategoryId('')
    setNote('')
    setDate(toLocalDateISO(new Date()))
    setTime(new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }))
    setTagIds([])
    setMakeTemplate(false)
    setTouched(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, record])

  /* Default category — the first suitable one: an empty select looks like an error */
  useEffect(() => {
    if (!open || editing || isTransfer) return
    if (categoryId && availableCategories.some((category) => String(category.id) === categoryId)) return
    setCategoryId(availableCategories[0] ? String(availableCategories[0].id) : '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, editing, isTransfer, availableCategories])

  /* The transfer destination can't equal the source: keep the selection valid */
  useEffect(() => {
    if (!open || !isTransfer) return
    if (toAccountId && toAccountId !== accountId) return
    setToAccountId(formAccounts.find((item) => item.id !== accountId)?.id ?? '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, isTransfer, accountId, formAccounts])

  const amountValue = parseAmount(amount)
  const amountInvalid = touched && amountValue === null
  const accountInvalid = touched && !accountId
  const toAccount = accounts.find((item) => item.id === toAccountId)
  const toAccountInvalid = touched && isTransfer && (!toAccountId || toAccountId === accountId)
  const categoryInvalid = touched && !isTransfer && !categoryId

  const accent =
    type === 'expense'
      ? {
          text: 'text-[var(--negative)]',
          ring: 'focus-visible:ring-[var(--negative)]/35',
          border: 'border-[var(--negative)]/45',
          strip: 'bg-[var(--negative)]',
          chip: 'accent-negative',
        }
      : type === 'transfer'
        ? {
            text: 'text-accent',
            ring: 'focus-visible:ring-[var(--accent-ring)]',
            border: 'border-accent/45',
            strip: 'bg-accent-fill',
            chip: '',
          }
        : {
            text: 'text-[var(--positive)]',
            ring: 'focus-visible:ring-[var(--positive)]/35',
            border: 'border-[var(--positive)]/45',
            strip: 'bg-[var(--positive)]',
            chip: 'accent-positive',
          }

  const toggleTag = (id: number) =>
    setTagIds((prev) => (prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]))

  const submit = async () => {
    setTouched(true)
    if (amountValue === null || !accountId) return
    if (isTransfer ? !toAccountId || toAccountId === accountId : !categoryId) return
    setPending(true)
    try {
      const payload = {
        account_id: Number(accountId),
        ...(isTransfer
          ? { transfer_account_id: Number(toAccountId) }
          : { category_id: Number(categoryId) }),
        amount: amountValue,
        currency_id: currency,
        type,
        date: toIso(date, time),
        note: note.trim() || null,
        tag_ids: tagIds,
      }

      if (editing && record) {
        await updateRecord(record.id, payload)
        toast({ title: t('state.saved'), description: t('records.updateSuccess'), tone: 'success' })
      } else {
        await createRecord(payload)
        toast({ title: t('records.created'), description: t('records.createSuccess'), tone: 'success' })
        // "Create a template" is a separate request: the template lives its own life
        if (makeTemplate) {
          await createTemplate({
            name: note.trim() || t('records.title'),
            type,
            amount: amountValue,
            currency_id: currency,
            account_id: Number(accountId),
            category_id: Number(categoryId),
            note: note.trim() || null,
            tag_ids: tagIds,
          })
          toast({ title: t('templates.created'), tone: 'success' })
        }
      }
      onOpenChange(false)
    } catch (caught) {
      toast({
        title: editing ? t('records.updateFailed') : t('records.createFailed'),
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
        title={editing ? t('recordForm.editTitle') : t('recordForm.title')}
        description={t('recordForm.subtitle')}
        className="[--dialog-w:min(760px,calc(100vw-2rem))]"
        footer={
          <div className="flex items-center justify-end gap-2">
            <Button variant="subtle" onClick={() => onOpenChange(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              onClick={() => void submit()}
              disabled={pending}
            >
              {pending ? t('state.saving') : editing ? t('common.save') : t('common.add')}
            </Button>
          </div>
        }
      >
        <div className="grid gap-5 md:grid-cols-[1.2fr_1fr]">
          {/* Left column: amount, account, category, note */}
          <div className={cn('space-y-4 rounded-md border p-4', accent.border)}>
            <div className={cn('flex gap-2', accent.chip)}>
              <SegmentedControl
                aria-label={t('recordForm.type')}
                value={type}
                onValueChange={(value) => setType(value as TransactionTypeValue)}
                items={[
                  { value: 'expense', label: t('recordForm.expense') },
                  { value: 'income', label: t('recordForm.income') },
                  { value: 'transfer', label: t('recordForm.transfer') },
                ]}
              />
            </div>

            <Field
              label={`${t('recordForm.amount')} (${currency})`}
              error={amountInvalid ? t('recordForm.amountInvalid') : undefined}
              required
            >
              <Input
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                onBlur={() => setTouched(true)}
                inputMode="decimal"
                placeholder="0,00"
                invalid={amountInvalid}
                className={cn('text-metric', accent.text)}
                autoFocus
              />
            </Field>

            <Field
              label={isTransfer ? t('recordForm.fromAccount') : t('recordForm.account')}
              error={accountInvalid ? t('recordForm.required') : undefined}
              required
            >
              <FilterSelect
                ariaLabel={isTransfer ? t('recordForm.fromAccount') : t('recordForm.account')}
                value={accountId}
                onValueChange={setAccountId}
                options={formAccounts.map((item) => ({
                  value: item.id,
                  label: `${item.name} · ${item.currency}`,
                  dotColor: item.tint,
                }))}
              />
            </Field>

            {isTransfer && (
              <Field
                label={t('recordForm.toAccount')}
                error={toAccountInvalid ? t('recordForm.required') : undefined}
                hint={
                  toAccount
                    ? toAccount.currency === currency
                      ? t('recordForm.transferSameCurrency')
                      : `${t('recordForm.transferDifferentCurrency')} · ${toAccount.currency}`
                    : undefined
                }
                required
              >
                <FilterSelect
                  ariaLabel={t('recordForm.toAccount')}
                  value={toAccountId}
                  onValueChange={setToAccountId}
                  options={formAccounts
                    .filter((item) => item.id !== accountId)
                    .map((item) => ({
                      value: item.id,
                      label: `${item.name} · ${item.currency}`,
                      dotColor: item.tint,
                    }))}
                />
              </Field>
            )}

            {!isTransfer && (
              <Field
                label={t('recordForm.category')}
                error={categoryInvalid ? t('recordForm.required') : undefined}
                required
              >
                <FilterSelect
                  ariaLabel={t('recordForm.category')}
                  value={categoryId}
                  onValueChange={setCategoryId}
                  options={categoryOptions}
                />
              </Field>
            )}

            <Field label={t('recordForm.note')}>
              <Textarea
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder={t('recordForm.notePlaceholder')}
                rows={2}
              />
            </Field>
          </div>

          {/* Right column: "other details" */}
          <div className="space-y-4">
            <div className="rounded-md bg-surface-2/60 p-3">
              <p className="mb-2 flex items-center gap-1.5 text-caption font-medium uppercase tracking-wide text-fg-tertiary">
                <CalendarClock className="size-3.5" aria-hidden="true" />
                {t('recordForm.date')}
              </p>
              <div className="grid grid-cols-2 gap-2">
                <Input
                  type="date"
                  value={date}
                  onChange={(event) => setDate(event.target.value)}
                  aria-label={t('recordForm.date')}
                  inputSize="sm"
                />
                <Input
                  type="time"
                  value={time}
                  onChange={(event) => setTime(event.target.value)}
                  aria-label={t('recordForm.time')}
                  inputSize="sm"
                />
              </div>
            </div>

            <div className="rounded-md bg-surface-2/60 p-3">
              <p className="mb-2 flex items-center gap-1.5 text-caption font-medium uppercase tracking-wide text-fg-tertiary">
                <Tags className="size-3.5" aria-hidden="true" />
                {t('recordForm.tags')}
              </p>
              {tags.length === 0 ? (
                <p className="text-caption text-fg-tertiary">{t('state.empty')}</p>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {tags.map((tag) => {
                    const active = tagIds.includes(tag.id)
                    return (
                      <button
                        key={tag.id}
                        type="button"
                        onClick={() => toggleTag(tag.id)}
                        aria-pressed={active}
                        className={cn(
                          'inline-flex items-center gap-1.5 rounded-pill border px-2 py-0.5 text-caption transition-colors',
                          active
                            ? 'border-accent bg-accent-soft text-accent-on-soft'
                            : 'border-stroke-subtle text-fg-secondary hover:border-stroke-strong',
                        )}
                      >
                        <span
                          className="size-1.5 rounded-pill"
                          style={{ backgroundColor: tag.color }}
                          aria-hidden="true"
                        />
                        {tag.name}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {!editing && !isTransfer && (
              <Switch
                checked={makeTemplate}
                onCheckedChange={setMakeTemplate}
                label={t('recordForm.templateFromRecord')}
              />
            )}

            {!isTransfer && availableCategories.length === 0 && (
              <p className="text-caption text-[var(--negative)]">
                {t('recordForm.noCategories')}{' '}
                <CategoryIcon name="circle" className="inline size-3" />
              </p>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
