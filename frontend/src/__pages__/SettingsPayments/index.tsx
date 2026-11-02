import { useState } from 'react'
import { Check, CreditCard, Plus, Trash2 } from 'lucide-react'
import { useI18n, type TranslationKey } from '@/i18n'
import { cn } from '@/__shared__/utils/cn'
import type { PaymentMethodKindValue, PlanPeriodValue } from '@/api/types'
import { ApiError, billingApi } from '@/api'
import { useApiQuery } from '@/hooks/useApi'
import { SettingsLayout } from '@/components/settings/SettingsLayout'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { SegmentedControl } from '@/components/ui/toggles'
import { FilterSelect } from '@/components/ui/overlays'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { useToast } from '@/components/ui/toast'
import { Amount } from '@/components/data/Amount'

/** Подписи периодов тарифа. */
const PERIOD_KEY: Record<PlanPeriodValue, TranslationKey> = {
  none: 'billing.period.none',
  month: 'billing.period.month',
  year: 'billing.period.year',
}

/** Подписи способов оплаты. */
const METHOD_KIND_KEY: Record<PaymentMethodKindValue, TranslationKey> = {
  card: 'billing.card',
  crypto: 'billing.crypto',
  bank_transfer: 'billing.bankTransfer',
}

/** Статусы платежа. */
const STATUS_KEY: Record<string, TranslationKey> = {
  succeeded: 'billing.status.succeeded',
  pending: 'billing.status.pending',
  failed: 'billing.status.failed',
  refunded: 'billing.status.refunded',
}

function formatDate(iso: string | null, locale: 'ru' | 'en') {
  if (!iso) return '—'
  return new Intl.DateTimeFormat(locale === 'ru' ? 'ru-RU' : 'en-US', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(iso))
}

/**
 * «Настройки → Платежи».
 *
 * Работает с приложением биллинга: тарифы и провайдеры приходят из
 * `/billing/plans` и `/billing/providers`, подписка — из `/billing/subscription`.
 * Оплата идёт через выбранного провайдера; в локальной среде это `mock`, который
 * сразу подтверждает платёж. Реальные провайдеры вернут `checkout_url`, и клиент
 * уйдёт на их страницу — поэтому форма карты здесь только собирает токен.
 */
export function SettingsPaymentsPage() {
  const { t, locale } = useI18n()
  const { toast } = useToast()

  const plans = useApiQuery(() => billingApi.listPlans(), [])
  const providers = useApiQuery(() => billingApi.listProviders(), [])
  const subscription = useApiQuery(() => billingApi.getSubscription(), [])
  const methods = useApiQuery(() => billingApi.listPaymentMethods(), [])
  const payments = useApiQuery(() => billingApi.listPayments(20), [])

  const [planOpen, setPlanOpen] = useState(false)
  const [planCode, setPlanCode] = useState('')
  const [providerCode, setProviderCode] = useState('')
  const [methodOpen, setMethodOpen] = useState(false)
  const [methodKind, setMethodKind] = useState<PaymentMethodKindValue>('card')
  const [cardNumber, setCardNumber] = useState('')
  const [pending, setPending] = useState(false)

  const current = subscription.data
  const currentPlan = plans.data?.find((plan) => plan.code === current?.plan_code)
  const selectable = plans.data?.filter((plan) => plan.is_active) ?? []
  const chosenProvider =
    providers.data?.find((provider) => provider.code === providerCode) ??
    providers.data?.find((provider) => provider.is_default)

  const openPlanDialog = () => {
    setPlanCode(current?.plan_code ?? selectable[0]?.code ?? '')
    setProviderCode(providers.data?.find((provider) => provider.is_default)?.code ?? '')
    setPlanOpen(true)
  }

  const changePlan = async () => {
    if (!planCode) return
    setPending(true)
    try {
      const session = await billingApi.changeSubscription(planCode, providerCode || undefined)
      // Реальный провайдер уводит на свою страницу оплаты
      if (session.requires_redirect && session.checkout_url) {
        window.location.assign(session.checkout_url)
        return
      }
      toast({ title: t('billing.planChanged'), description: session.status, tone: 'success' })
      setPlanOpen(false)
      await Promise.all([subscription.reload(), payments.reload(), methods.reload()])
    } catch (caught) {
      toast({
        title: t('billing.planChangeFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    } finally {
      setPending(false)
    }
  }

  const cancelPlan = async () => {
    setPending(true)
    try {
      await billingApi.cancelSubscription(false)
      toast({ title: t('billing.cancelAtPeriodEnd'), tone: 'info' })
      await subscription.reload()
    } catch (caught) {
      toast({
        title: t('billing.planChangeFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    } finally {
      setPending(false)
    }
  }

  const addMethod = async () => {
    // Реальная форма карты живёт на стороне провайдера: здесь только «токен»
    const digits = cardNumber.replace(/\D/g, '')
    setPending(true)
    try {
      await billingApi.attachPaymentMethod({
        provider: chosenProvider?.code,
        kind: methodKind,
        token: digits ? `tok_${digits.slice(-4)}` : undefined,
        makeDefault: (methods.data?.length ?? 0) === 0,
      })
      toast({ title: t('billing.methodAdded'), tone: 'success' })
      setMethodOpen(false)
      setCardNumber('')
      await methods.reload()
    } catch (caught) {
      toast({
        title: t('common.error'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    } finally {
      setPending(false)
    }
  }

  const makeDefault = async (id: number) => {
    try {
      await billingApi.makePaymentMethodDefault(id)
      await methods.reload()
    } catch (caught) {
      toast({
        title: t('common.error'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    }
  }

  const removeMethod = async (id: number) => {
    try {
      await billingApi.deletePaymentMethod(id)
      await methods.reload()
    } catch (caught) {
      toast({
        title: t('common.error'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    }
  }

  return (
    <SettingsLayout title={t('payments.title')} subtitle={t('payments.subtitle')}>
      <div className="space-y-4">
        {/* Текущий тариф */}
        <Card>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-label font-semibold text-fg-primary">{t('billing.currentPlan')}</h2>
              <p className="mt-1 flex flex-wrap items-baseline gap-1.5 text-title font-semibold tracking-snug text-fg-primary">
                {current?.plan_name ?? t('state.loading')}
                {currentPlan && currentPlan.price > 0 && (
                  <span className="text-label font-normal text-fg-secondary">
                    ·{' '}
                    <Amount value={currentPlan.price} currency={currentPlan.currency} size="sm" tone="neutral" />{' '}
                    {t(PERIOD_KEY[currentPlan.period])}
                  </span>
                )}
              </p>
              <p className="mt-1 text-caption text-fg-tertiary">
                {current?.status === 'active'
                  ? `${t('payments.until')} ${formatDate(current.current_period_end, locale)}`
                  : (current?.status ?? '')}
                {current?.cancel_at_period_end && ` · ${t('billing.cancelAtPeriodEnd')}`}
              </p>
              <ul className="mt-3 space-y-1.5">
                {(currentPlan?.features.length
                  ? currentPlan.features
                  : [t('payments.feature1'), t('payments.feature2'), t('payments.feature3')]
                ).map((feature) => (
                  <li key={feature} className="flex items-center gap-1.5 text-label text-fg-secondary">
                    <Check className="size-3.5 text-[var(--positive)]" aria-hidden="true" />
                    {feature}
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex flex-col items-end gap-2">
              <Button variant="subtle" size="sm" onClick={openPlanDialog}>
                {t('billing.changePlan')}
              </Button>
              {current && current.plan_code !== 'free' && !current.cancel_at_period_end && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-caption text-[var(--negative)]"
                  disabled={pending}
                  onClick={() => void cancelPlan()}
                >
                  {t('billing.cancelPlan')}
                </Button>
              )}
            </div>
          </div>
        </Card>

        {/* Способы оплаты */}
        <Card className="p-0">
          <div className="flex items-center justify-between gap-2 border-b border-stroke-subtle px-4 py-2.5">
            <h2 className="text-label font-semibold text-fg-primary">{t('payments.methods')}</h2>
            <Button size="sm" className="gap-1.5" onClick={() => setMethodOpen(true)}>
              <Plus className="size-4" aria-hidden="true" />
              {t('billing.addMethod')}
            </Button>
          </div>

          {(methods.data?.length ?? 0) === 0 && (
            <p className="px-4 py-6 text-center text-caption text-fg-tertiary">{t('billing.noMethods')}</p>
          )}

          <ul>
            {methods.data?.map((method, index) => (
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
                    {method.brand ?? t(METHOD_KIND_KEY[method.kind])}
                    {method.last4 ? ` ···· ${method.last4}` : ''}
                  </p>
                  <p className="text-caption text-fg-tertiary">
                    {method.provider}
                    {method.is_default && ` · ${t('billing.defaultMethod')}`}
                  </p>
                </div>
                {!method.is_default && (
                  <Button variant="ghost" size="sm" onClick={() => void makeDefault(method.id)}>
                    {t('billing.makeDefault')}
                  </Button>
                )}
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label={t('billing.removeMethod')}
                  onClick={() => void removeMethod(method.id)}
                >
                  <Trash2 className="size-4 text-[var(--negative)]" aria-hidden="true" />
                </Button>
              </li>
            ))}
          </ul>
        </Card>

        {/* История платежей */}
        <Card className="p-0">
          <div className="border-b border-stroke-subtle px-4 py-2.5">
            <h2 className="text-label font-semibold text-fg-primary">{t('billing.paymentHistory')}</h2>
          </div>

          {(payments.data?.length ?? 0) === 0 && (
            <p className="px-4 py-6 text-center text-caption text-fg-tertiary">{t('billing.noPayments')}</p>
          )}

          <ul>
            {payments.data?.map((row, index) => (
              <li
                key={row.id}
                className={cn(
                  'flex items-center gap-3 px-4 py-2.5',
                  index > 0 && 'border-t border-stroke-subtle',
                )}
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-label text-fg-primary">
                    {row.plan_code ?? row.kind} · {row.provider}
                  </p>
                  <p className="text-caption text-fg-tertiary">
                    {formatDate(row.created_at, locale)}
                    {row.failure_reason && ` · ${row.failure_reason}`}
                  </p>
                </div>
                <span
                  className={cn(
                    'rounded-pill px-2 py-0.5 text-caption',
                    row.status === 'succeeded'
                      ? 'bg-[var(--positive-soft)] text-[var(--positive)]'
                      : row.status === 'failed'
                        ? 'bg-[var(--negative-soft)] text-[var(--negative)]'
                        : 'bg-surface-2 text-fg-secondary',
                  )}
                >
                  {t(STATUS_KEY[row.status] ?? 'billing.status.pending')}
                </span>
                <Amount value={-row.amount} currency={row.currency} size="sm" />
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {/* Смена тарифа */}
      <Dialog open={planOpen} onOpenChange={setPlanOpen}>
        <DialogContent
          title={t('billing.changePlan')}
          description={t('payments.changePlanHint')}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => setPlanOpen(false)}>
                {t('common.cancel')}
              </Button>
              <Button onClick={() => void changePlan()} disabled={!planCode || pending}>
                {pending ? t('state.saving') : t('common.save')}
              </Button>
            </div>
          }
        >
          <div className="space-y-3">
            <ul className="space-y-2">
              {selectable.map((option) => (
                <li key={option.code}>
                  <button
                    type="button"
                    onClick={() => setPlanCode(option.code)}
                    aria-pressed={planCode === option.code}
                    className={cn(
                      'flex w-full items-center gap-3 rounded-md border p-3 text-left transition-colors',
                      planCode === option.code
                        ? 'border-accent bg-accent-soft/40'
                        : 'border-stroke-subtle hover:bg-surface-2/70',
                    )}
                  >
                    <span
                      className={cn(
                        'grid size-4 shrink-0 place-items-center rounded-pill border',
                        planCode === option.code ? 'border-accent bg-accent' : 'border-stroke-strong',
                      )}
                      aria-hidden="true"
                    >
                      {planCode === option.code && <Check className="size-3 text-accent-fg" />}
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-label font-medium text-fg-primary">{option.name}</span>
                      <span className="block text-caption text-fg-tertiary">
                        {option.description ?? option.features.join(' · ')}
                      </span>
                    </span>
                    <span className="shrink-0 text-label font-semibold text-fg-primary">
                      <Amount value={option.price} currency={option.currency} size="sm" />
                      <span className="ml-1 text-caption font-normal text-fg-tertiary">
                        {t(PERIOD_KEY[option.period])}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>

            <Field
              label={t('billing.provider')}
              hint={chosenProvider?.is_mock ? t('billing.mockProvider') : undefined}
            >
              <FilterSelect
                ariaLabel={t('billing.provider')}
                value={providerCode}
                onValueChange={setProviderCode}
                options={(providers.data ?? []).map((provider) => ({
                  value: provider.code,
                  label: provider.is_configured
                    ? `${provider.title}${provider.is_mock ? ` (${t('billing.mockProvider')})` : ''}`
                    : `${provider.title} — ${t('billing.providerUnavailable')}`,
                }))}
              />
            </Field>
          </div>
        </DialogContent>
      </Dialog>

      {/* Добавление способа оплаты */}
      <Dialog open={methodOpen} onOpenChange={setMethodOpen}>
        <DialogContent
          title={t('billing.addMethod')}
          description={t('payments.addCardHint')}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => setMethodOpen(false)}>
                {t('common.cancel')}
              </Button>
              <Button onClick={() => void addMethod()} disabled={pending}>
                {pending ? t('state.saving') : t('common.save')}
              </Button>
            </div>
          }
        >
          <div className="space-y-3">
            <SegmentedControl
              aria-label={t('payments.methods')}
              value={methodKind}
              onValueChange={(value) => setMethodKind(value as PaymentMethodKindValue)}
              items={(Object.keys(METHOD_KIND_KEY) as PaymentMethodKindValue[]).map((kind) => ({
                value: kind,
                label: t(METHOD_KIND_KEY[kind]),
              }))}
            />

            {methodKind === 'card' && (
              <Field label={t('payments.cardNumber')}>
                <Input
                  value={cardNumber}
                  onChange={(event) =>
                    setCardNumber(
                      event.target.value
                        .replace(/\D/g, '')
                        .slice(0, 16)
                        .replace(/(.{4})/g, '$1 ')
                        .trim(),
                    )
                  }
                  placeholder="[CREDIT_CARD]"
                  inputMode="numeric"
                  iconLeft={<CreditCard className="size-4" />}
                />
              </Field>
            )}

            <Field label={t('billing.provider')}>
              <FilterSelect
                ariaLabel={t('billing.provider')}
                value={providerCode}
                onValueChange={setProviderCode}
                options={(providers.data ?? []).map((provider) => ({
                  value: provider.code,
                  label: provider.title,
                }))}
              />
            </Field>
          </div>
        </DialogContent>
      </Dialog>
    </SettingsLayout>
  )
}
