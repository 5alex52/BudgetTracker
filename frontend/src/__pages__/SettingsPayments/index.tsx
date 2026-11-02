import { useState } from 'react'
import { Check, CreditCard, Plus, Trash2 } from 'lucide-react'
import { useI18n } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import { SettingsLayout } from '@/components/settings/SettingsLayout'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { Switch } from '@/components/ui/toggles'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { useToast } from '@/components/ui/toast'
import { Amount } from '@/components/data/Amount'

interface PaymentMethod {
  id: string
  brand: string
  last4: string
  expiry: string
  primary?: boolean
}

const INITIAL_METHODS: PaymentMethod[] = [
  { id: 'pm-1', brand: 'Visa', last4: '4242', expiry: '09/28', primary: true },
  { id: 'pm-2', brand: 'Mastercard', last4: '8810', expiry: '03/27' },
]

const HISTORY = [
  { id: 'inv-3', date: '01.11.2026', label: 'Premium · месяц', amount: -4.99, status: 'paid' },
  { id: 'inv-2', date: '01.10.2026', label: 'Premium · месяц', amount: -4.99, status: 'paid' },
  { id: 'inv-1', date: '01.09.2026', label: 'Premium · месяц', amount: -4.99, status: 'paid' },
]

/**
 * «Настройки → Платежи».
 *
 * В референсе экрана нет, поэтому состав собран по смыслу раздела: текущий
 * план, способы оплаты, автопродление и история списаний. Форма добавления
 * карты — демонстрационная: реальное списание появится с платёжным провайдером.
 */
export function SettingsPaymentsPage() {
  const { t } = useI18n()
  const { toast } = useToast()
  const [methods, setMethods] = useState<PaymentMethod[]>(INITIAL_METHODS)
  const [autoRenew, setAutoRenew] = useState(true)
  const [open, setOpen] = useState(false)
  const [planOpen, setPlanOpen] = useState(false)
  /** Выбранный тариф: бесплатный или премиум с периодом оплаты */
  const [plan, setPlan] = useState<'free' | 'monthly' | 'yearly'>('monthly')
  const [number, setNumber] = useState('')
  const [expiry, setExpiry] = useState('')

  const addCard = () => {
    const digits = number.replace(/\D/g, '')
    if (digits.length < 4) return
    setMethods((prev) => [
      ...prev,
      { id: `pm-${Date.now()}`, brand: digits.startsWith('4') ? 'Visa' : 'Mastercard', last4: digits.slice(-4), expiry: expiry || '—' },
    ])
    setNumber('')
    setExpiry('')
    setOpen(false)
    toast({ title: t('payments.addCard'), description: `•••• ${digits.slice(-4)}`, tone: 'success' })
  }

  return (
    <SettingsLayout title={t('payments.title')} subtitle={t('payments.subtitle')}>
      <div className="space-y-4">
        {/* Текущий план */}
        <Card>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-label font-semibold text-fg-primary">{t('payments.plan')}</h2>
              <p className="mt-1 flex items-baseline gap-1.5 text-title font-semibold tracking-snug text-fg-primary">
                Premium
                <span className="text-label font-normal text-fg-secondary">
                  · <Amount value={4.99} currency="BYN" size="sm" tone="neutral" /> {t('payments.perMonth')}
                </span>
              </p>
              <ul className="mt-3 space-y-1.5">
                {[t('payments.feature1'), t('payments.feature2'), t('payments.feature3')].map((feature) => (
                  <li key={feature} className="flex items-center gap-1.5 text-label text-fg-secondary">
                    <Check className="size-3.5 text-[var(--positive)]" aria-hidden="true" />
                    {feature}
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex flex-col items-end gap-2">
              <Switch checked={autoRenew} onCheckedChange={setAutoRenew} label={t('payments.autoRenew')} />
              <Button variant="subtle" size="sm" onClick={() => setPlanOpen(true)}>
                {t('payments.changePlan')}
              </Button>
            </div>
          </div>
        </Card>

        {/* Способы оплаты */}
        <Card className="p-0">
          <div className="flex items-center justify-between gap-2 border-b border-stroke-subtle px-4 py-2.5">
            <h2 className="text-label font-semibold text-fg-primary">{t('payments.methods')}</h2>
            <Button size="sm" className="gap-1.5" onClick={() => setOpen(true)}>
              <Plus className="size-4" aria-hidden="true" />
              {t('payments.addCard')}
            </Button>
          </div>
          <ul>
            {methods.map((method, index) => (
              <li
                key={method.id}
                className={cn(
                  'flex items-center gap-3 px-4 py-2.5',
                  index > 0 && 'border-t border-stroke-subtle',
                )}
              >
                <span className="grid size-8 shrink-0 place-items-center rounded-sm bg-surface-2 text-fg-secondary">
                  <CreditCard className="size-4" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-label font-medium text-fg-primary">
                    {method.brand} ···· {method.last4}
                  </p>
                  <p className="text-caption text-fg-tertiary">
                    {t('payments.until')} {method.expiry}
                    {method.primary && ` · ${t('payments.primary')}`}
                  </p>
                </div>
                {!method.primary && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setMethods((prev) => prev.map((row) => ({ ...row, primary: row.id === method.id })))}
                  >
                    {t('payments.makePrimary')}
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={t('common.delete')}
                  onClick={() => setMethods((prev) => prev.filter((row) => row.id !== method.id))}
                >
                  <Trash2 className="size-4 text-[var(--negative)]" aria-hidden="true" />
                </Button>
              </li>
            ))}
          </ul>
        </Card>

        {/* История */}
        <Card className="p-0">
          <div className="border-b border-stroke-subtle px-4 py-2.5">
            <h2 className="text-label font-semibold text-fg-primary">{t('payments.history')}</h2>
          </div>
          <ul>
            {HISTORY.map((row, index) => (
              <li
                key={row.id}
                className={cn('flex items-center gap-3 px-4 py-2.5', index > 0 && 'border-t border-stroke-subtle')}
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-label text-fg-primary">{row.label}</p>
                  <p className="text-caption text-fg-tertiary">{row.date}</p>
                </div>
                <span className="rounded-pill bg-[var(--positive-soft)] px-2 py-0.5 text-caption text-[var(--positive)]">
                  {t('payments.paid')}
                </span>
                <Amount value={row.amount} currency="BYN" size="sm" />
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent
          title={t('payments.addCard')}
          description={t('payments.addCardHint')}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => setOpen(false)}>
                {t('common.cancel')}
              </Button>
              <Button onClick={addCard} disabled={number.replace(/\D/g, '').length < 12}>
                {t('common.save')}
              </Button>
            </div>
          }
        >
          <div className="space-y-3">
            <Field label={t('payments.cardNumber')}>
              <Input
                value={number}
                onChange={(event) =>
                  setNumber(
                    event.target.value
                      .replace(/\D/g, '')
                      .slice(0, 16)
                      .replace(/(.{4})/g, '$1 ')
                      .trim(),
                  )
                }
                placeholder="0000 0000 0000 0000"
                inputMode="numeric"
                autoFocus
                iconLeft={<CreditCard className="size-4" />}
              />
            </Field>
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label={t('payments.expiry')}>
                <Input
                  value={expiry}
                  onChange={(event) => setExpiry(event.target.value.slice(0, 5))}
                  placeholder="MM/YY"
                  inputMode="numeric"
                />
              </Field>
              <Field label="CVC">
                <Input placeholder="•••" inputMode="numeric" type="password" />
              </Field>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={planOpen} onOpenChange={setPlanOpen}>
        <DialogContent
          title={t('payments.changePlan')}
          description={t('payments.changePlanHint')}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => setPlanOpen(false)}>
                {t('common.cancel')}
              </Button>
              <Button
                onClick={() => {
                  setPlanOpen(false)
                  toast({ title: t('payments.changePlan'), description: t(`payments.plan.${plan}`), tone: 'success' })
                }}
              >
                {t('common.save')}
              </Button>
            </div>
          }
        >
          <ul className="space-y-2">
            {(['free', 'monthly', 'yearly'] as const).map((option) => (
              <li key={option}>
                <button
                  type="button"
                  onClick={() => setPlan(option)}
                  aria-pressed={plan === option}
                  className={cn(
                    'flex w-full items-center gap-3 rounded-md border p-3 text-left transition-colors',
                    plan === option ? 'border-accent bg-accent-soft/40' : 'border-stroke-subtle hover:bg-surface-2/70',
                  )}
                >
                  <span
                    className={cn(
                      'grid size-4 shrink-0 place-items-center rounded-pill border',
                      plan === option ? 'border-accent bg-accent' : 'border-stroke-strong',
                    )}
                    aria-hidden="true"
                  >
                    {plan === option && <Check className="size-3 text-accent-fg" />}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-label font-medium text-fg-primary">{t(`payments.plan.${option}`)}</span>
                    <span className="block text-caption text-fg-tertiary">{t(`payments.planHint.${option}`)}</span>
                  </span>
                  <span className="shrink-0 text-label font-semibold text-fg-primary">
                    {t(`payments.planPrice.${option}`)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </DialogContent>
      </Dialog>
    </SettingsLayout>
  )
}
