import { useEffect, useMemo, useState } from 'react'
import { CalendarClock, Tag } from 'lucide-react'
import { useI18n } from '@/i18n'
import { accounts, categories, currencies, subcategories, type RecordItem } from '@/__shared__/mock/finance'
import { useRecordsStore } from '@/store/records'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { Button } from '@/components/ui/button'
import { Field, Input, Textarea } from '@/components/ui/field'
import { SegmentedControl, Switch } from '@/components/ui/toggles'
import { FilterSelect } from '@/components/ui/overlays'
import { useToast } from '@/components/ui/toast'
import { CategoryIcon } from '@/__shared__/utils/category-icon'
import { cn } from '@/__shared__/utils/cn'

type RecordType = 'expense' | 'income' | 'transfer'

/**
 * «Добавление записи» — двухколоночный стеклянный модал из референса.
 * Справа «Другие детали»; на узких экранах колонки складываются.
 * Сабмит ничего не пишет в данные: пока нет API, это демонстрация формы.
 */
export function AddRecordDialog({
  open,
  onOpenChange,
  record,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Если передан — модал работает в режиме редактирования записи */
  record?: RecordItem | null
}) {
  const editing = Boolean(record)
  const { t } = useI18n()
  const { toast } = useToast()

  const [type, setType] = useState<RecordType>('expense')
  const [amount, setAmount] = useState('')
  const [account, setAccount] = useState(accounts[0]?.id ?? '')
  const [toAccount, setToAccount] = useState(accounts[1]?.id ?? '')
  const [amountTo, setAmountTo] = useState('')
  const [category, setCategory] = useState(categories[0]?.name ?? '')
  const [note, setNote] = useState('')
  const [payer, setPayer] = useState('')
  const [paymentType, setPaymentType] = useState('card')
  const [acknowledged, setAcknowledged] = useState(true)
  const [makeTemplate, setMakeTemplate] = useState(false)
  const [touched, setTouched] = useState(false)

  const { upsert, nextId } = useRecordsStore()

  useEffect(() => {
    if (!open) return
    if (record) {
      setType(record.type)
      setAmount(String(Math.abs(record.amount)).replace('.', ','))
      setAccount(accounts.find((item) => item.name === record.account)?.id ?? accounts[0]?.id ?? '')
      setCategory(record.category)
      setNote(record.note ?? '')
      setPayer(record.payer ?? '')
      setTouched(false)
    } else {
      setType('expense')
      setAmount('')
      setCategory(categories[0]?.name ?? '')
      setNote('')
      setPayer('')
      setTouched(false)
    }
  }, [open, record])

  const amountInvalid = touched && !amount.trim()

  /* Акцент формы по типу: расход — красный, доход — зелёный, перевод — синий */
  const accent =
    type === 'expense'
      ? { text: 'text-[var(--negative)]', ring: 'focus-visible:ring-[var(--negative)]/35', border: 'border-[var(--negative)]/45', strip: 'bg-[var(--negative)]', chip: 'accent-negative' }
      : type === 'income'
        ? { text: 'text-[var(--positive)]', ring: 'focus-visible:ring-[var(--positive)]/35', border: 'border-[var(--positive)]/45', strip: 'bg-[var(--positive)]', chip: 'accent-positive' }
        : { text: 'text-accent', ring: 'focus-visible:ring-[var(--accent-ring)]', border: 'border-accent/45', strip: 'bg-accent', chip: 'accent-default' }

  /* Категории с подкатегориями: группы «родитель → дети» */
  const categoryGroups = useMemo(
    () =>
      categories.map((parent) => ({
        label: parent.name,
        options: [
          { value: parent.name, label: parent.name },
          ...subcategories
            .filter((sub) => sub.parent === parent.id)
            .map((sub) => ({ value: sub.name, label: sub.name, indent: true, dotColor: sub.color })),
        ],
      })),
    [],
  )

  /* ----------------------------- перевод ----------------------------- */

  const fromAcc = accounts.find((item) => item.id === account)
  const toAcc = accounts.find((item) => item.id === toAccount)
  const rateOf = (code?: string) => currencies.find((item) => item.code === code)?.rate ?? 1
  const fromPerBase = rateOf(fromAcc?.currency)
  const toPerBase = rateOf(toAcc?.currency)
  /** Сколько единиц валюты получателя приходится на 1 единицу валюты отправителя. */
  const conversion = toPerBase === 0 ? 1 : fromPerBase / toPerBase
  const sameCurrency = fromAcc?.currency === toAcc?.currency

  const parsedFrom = Number(amount.replace(',', '.')) || 0
  const autoTo = parsedFrom > 0 ? (parsedFrom * conversion).toFixed(2).replace('.', ',') : ''

  const effectiveTo = amountTo.trim() ? amountTo : autoTo
  const effectiveRate =
    parsedFrom > 0 && Number(effectiveTo.replace(',', '.')) > 0
      ? Number(effectiveTo.replace(',', '.')) / parsedFrom
      : conversion

  const submit = (andNew = false) => {
    setTouched(true)
    if (!amount.trim()) return

    const parsed = Number(amount.replace(',', '.')) || 0
    const accountName = accounts.find((item) => item.id === account)?.name ?? accounts[0]?.name ?? 'Alfa'
    const matchedCategory = categories.find((item) => item.name === category)
    const matchedSub = subcategories.find((item) => item.name === category)

    const next: RecordItem = {
      id: record?.id ?? nextId(),
      type,
      category: category || matchedCategory?.name || '—',
      categoryIcon: matchedCategory?.icon ?? matchedSub?.icon ?? 'arrow-left-right',
      categoryColor: matchedCategory?.color ?? matchedSub?.color ?? 'var(--accent)',
      account: accountName,
      accountTint: accounts.find((item) => item.id === account)?.tint ?? 'var(--accent)',
      amount: type === 'income' ? Math.abs(parsed) : -Math.abs(parsed),
      currency: fromAcc?.currency ?? 'BYN',
      date: record?.date ?? new Date().toISOString().slice(0, 10),
      time: record?.time ?? new Date().toTimeString().slice(0, 5),
      note: note || undefined,
      payer: payer || undefined,
    }

    upsert(next)
    toast({
      title: editing ? t('common.save') : t('recordForm.submit'),
      description:
        type === 'transfer'
          ? `${fromAcc?.name} → ${toAcc?.name}: ${amount} ${fromAcc?.currency} → ${effectiveTo} ${toAcc?.currency}`
          : `${amount} · ${next.category}`,
      tone: 'success',
    })

    if (andNew) {
      setAmount('')
      setNote('')
      setTouched(false)
      return
    }
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        title={editing ? t('recordForm.editTitle') : t('recordForm.title')}
        className="[--dialog-w:min(880px,calc(100vw-2rem))]"
        footer={
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="subtle" onClick={() => onOpenChange(false)}>
              {t('common.cancel')}
            </Button>
            {!editing && (
              <Button variant="glass" onClick={() => submit(true)}>
                {t('recordForm.submitAndNew')}
              </Button>
            )}
            <Button onClick={() => submit(false)} className={cn(accent.chip === 'accent-negative' && 'bg-[var(--negative-fill)] text-white hover:bg-[var(--negative-fill)]/90', accent.chip === 'accent-positive' && 'bg-[var(--positive-fill)] text-white hover:bg-[var(--positive-fill)]/90')}>
              {editing ? t('common.save') : t('recordForm.submit')}
            </Button>
          </div>
        }
      >
        <div className="space-y-4">
          <span className={cn('block h-[3px] w-full rounded-pill', accent.strip)} aria-hidden="true" />
          <SegmentedControl
            aria-label={t('recordForm.title')}
            value={type}
            onValueChange={(value) => {
              setType(value as RecordType)
              setTouched(false)
            }}
            items={[
              { value: 'expense', label: t('recordForm.expense') },
              { value: 'income', label: t('recordForm.income') },
              { value: 'transfer', label: t('recordForm.transfer') },
            ]}
          />

          <Field label={t('recordForm.templatePlaceholder')}>
            <FilterSelect
              ariaLabel={t('recordForm.templatePlaceholder')}
              value="none"
              onValueChange={() => undefined}
              options={[{ value: 'none', label: t('recordForm.choose') }]}
            />
          </Field>

          <div className="grid gap-4 md:grid-cols-[1.1fr_1fr]">
            {/* Основное */}
            <div className="space-y-3">
              {type === 'transfer' ? (
                <>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <Field label={t('recordForm.fromAccount')}>
                      <FilterSelect
                        ariaLabel={t('recordForm.fromAccount')}
                        value={account}
                        onValueChange={setAccount}
                        options={accounts.map((item) => ({
                          value: item.id,
                          label: `${item.name} · ${item.currency}`,
                        }))}
                      />
                    </Field>
                    <Field label={t('recordForm.toAccount')}>
                      <FilterSelect
                        ariaLabel={t('recordForm.toAccount')}
                        value={toAccount}
                        onValueChange={setToAccount}
                        options={accounts
                          .filter((item) => item.id !== account)
                          .map((item) => ({ value: item.id, label: `${item.name} · ${item.currency}` }))}
                      />
                    </Field>
                  </div>

                  <div className="grid gap-3 sm:grid-cols-2">
                    <Field
                      label={`${t('recordForm.transferAmount')} *`}
                      error={amountInvalid ? t('recordForm.required') : undefined}
                    >
                      <Input
                        inputSize="lg"
                        value={amount}
                        onChange={(event) => {
                          setAmount(event.target.value)
                          setAmountTo('')
                        }}
                        onBlur={() => {
                          if (amount.trim()) setTouched(true)
                        }}
                        invalid={amountInvalid}
                        placeholder="0,00"
                        inputMode="decimal"
                        className={cn('font-medium', accent.text)}
                        autoFocus
                      />
                      <span className="mt-1 block text-caption text-fg-tertiary">{fromAcc?.currency}</span>
                    </Field>

                    <Field label={t('recordForm.transferAmount')}>
                      <Input
                        inputSize="lg"
                        value={effectiveTo}
                        onChange={(event) => setAmountTo(event.target.value)}
                        placeholder="0,00"
                        inputMode="decimal"
                        disabled={sameCurrency}
                      />
                      <span className="mt-1 block text-caption text-fg-tertiary">{toAcc?.currency}</span>
                    </Field>
                  </div>

                  <p className="rounded-sm bg-surface-2/60 px-3 py-2 text-caption text-fg-secondary">
                    {sameCurrency
                      ? t('recordForm.transferSameCurrency')
                      : `${t('recordForm.transferDifferentCurrency')} · ${t('recordForm.transferRate')} 1 ${fromAcc?.currency} = ${effectiveRate.toFixed(4).replace('.', ',')} ${toAcc?.currency}`}
                  </p>

                  <Field label={t('recordForm.dateTime')}>
                    <Input
                      defaultValue="2025-10-11T16:27"
                      type="datetime-local"
                      iconLeft={<CalendarClock className="size-4" />}
                    />
                  </Field>
                </>
              ) : (
                <>
              <Field
                label={t('recordForm.amount')}
                error={amountInvalid ? t('recordForm.required') : undefined}
              >
                <Input
                  inputSize="lg"
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                  onBlur={() => {
                    if (amount.trim()) setTouched(true)
                  }}
                  invalid={amountInvalid}
                  placeholder="0,00"
                  inputMode="decimal"
                  className={cn('font-medium', accent.text)}
                  autoFocus
                />
              </Field>

              <Field label={t('recordForm.account')}>
                <FilterSelect
                  ariaLabel={t('recordForm.account')}
                  value={account}
                  onValueChange={setAccount}
                  options={accounts.map((item) => ({ value: item.id, label: `${item.name} · ${item.currency}` }))}
                />
              </Field>

              <Field label={t('recordForm.category')}>
                <FilterSelect
                  ariaLabel={t('recordForm.category')}
                  value={category}
                  onValueChange={setCategory}
                  options={[]}
                  groups={categoryGroups}
                />
              </Field>

              {/* Плитки категорий: быстрый выбор, как в мобильном референсе */}
              <div className="flex flex-wrap gap-1.5">
                {categories.slice(0, 5).map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => setCategory(item.name)}
                    aria-pressed={category === item.name}
                    className={cn(
                      'flex items-center gap-1.5 rounded-pill border px-2.5 py-1 text-caption transition-colors duration-fast',
                      category === item.name
                        ? 'border-accent bg-accent/10 text-accent'
                        : 'border-stroke-subtle text-fg-secondary hover:border-stroke-strong',
                    )}
                  >
                    <CategoryIcon name={item.icon} className="size-3.5" />
                    {item.name}
                  </button>
                ))}
              </div>

              {/* Подкатегории выбранной родительской категории */}
              {subcategories.filter((sub) => categories.find((parent) => parent.name === category)?.id === sub.parent).length > 0 && (
                <div className="flex flex-wrap gap-1.5 pl-1">
                  {subcategories
                    .filter((sub) => categories.find((parent) => parent.name === category)?.id === sub.parent)
                    .map((sub) => (
                      <button
                        key={sub.id}
                        type="button"
                        onClick={() => setCategory(sub.name)}
                        aria-pressed={category === sub.name}
                        className={cn(
                          'flex items-center gap-1.5 rounded-pill border px-2 py-0.5 text-caption transition-colors duration-fast',
                          category === sub.name
                            ? 'border-accent bg-accent/10 text-accent'
                            : 'border-stroke-subtle text-fg-tertiary hover:border-stroke-strong hover:text-fg-secondary',
                        )}
                      >
                        <span className="size-1.5 rounded-pill" style={{ backgroundColor: sub.color }} aria-hidden="true" />
                        {sub.name}
                      </button>
                    ))}
                </div>
              )}

              <Field label={t('recordForm.dateTime')}>
                <Input
                  defaultValue="2025-10-11T16:27"
                  type="datetime-local"
                  iconLeft={<CalendarClock className="size-4" />}
                />
              </Field>
                </>
              )}
            </div>

            {/* Другие детали */}
            <div className="space-y-3 rounded-md bg-surface-2/60 p-3">
              <p className="text-caption font-medium uppercase tracking-wide text-fg-tertiary">
                {t('recordForm.otherDetails')}
              </p>

              <Field label={t('recordForm.note')}>
                <Textarea
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder={t('recordForm.notePlaceholder')}
                  rows={3}
                />
              </Field>

              <Field label={t('recordForm.tags')}>
                <Input placeholder={t('recordForm.choose')} iconLeft={<Tag className="size-4" />} />
              </Field>

              <Field label={t('recordForm.payer')}>
                <Input
                  value={payer}
                  onChange={(event) => setPayer(event.target.value)}
                  placeholder={t('recordForm.choose')}
                />
              </Field>

              <Field label={t('recordForm.paymentType')}>
                <FilterSelect
                  ariaLabel={t('recordForm.paymentType')}
                  value={paymentType}
                  onValueChange={setPaymentType}
                  options={[
                    { value: 'card', label: t('recordForm.paymentType') },
                    { value: 'cash', label: t('recordForm.cash') },
                  ]}
                />
              </Field>

              <Switch
                checked={acknowledged}
                onCheckedChange={setAcknowledged}
                label={t('recordForm.acknowledged')}
              />
              <Switch
                checked={makeTemplate}
                onCheckedChange={setMakeTemplate}
                label={t('recordForm.templateFromRecord')}
              />
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
