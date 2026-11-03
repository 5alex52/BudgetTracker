import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Lock, Pencil, RotateCcw, Sparkles } from 'lucide-react'
import { useI18n } from '@/i18n'
import { ApiError } from '@/api'
import { useFinanceStore } from '@/store/finance'
import type { CurrencyRate } from '@/__shared__/types/models'
import { SettingsLayout } from '@/components/settings/SettingsLayout'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { Dialog, DialogContent } from '@/components/ui/dialogs'
import { useToast } from '@/components/ui/toast'
import { useEntitlements } from '@/hooks/useEntitlements'

/**
 * «Настройки → Валюты».
 *
 * Справочник курсов общий для всех — его ведёт сервис. Пользователь может
 * задать свой курс для любой валюты: он используется только в его расчётах
 * (`PUT /currencies/{code}/rate`) и сбрасывается к справочному одним нажатием.
 *
 * Валюты, которые пользователь использует в своих счетах, показываются сверху
 * в обычном цвете. Остальные идут ниже приглушённым тоном — это справочник,
 * который может пригодиться, если счёт будет открыт в новой валюте.
 */
export function SettingsCurrenciesPage() {
  const { t } = useI18n()
  const { toast } = useToast()
  const rates = useFinanceStore((state) => state.rates)
  const accounts = useFinanceStore((state) => state.accounts)
  const setUserRate = useFinanceStore((state) => state.setUserRate)
  const resetUserRate = useFinanceStore((state) => state.resetUserRate)

  const navigate = useNavigate()
  const entitlements = useEntitlements()
  const multiCurrency = entitlements.data?.multi_currency === true

  const [draft, setDraft] = useState<CurrencyRate | null>(null)
  const [value, setValue] = useState('')
  const [pending, setPending] = useState(false)

  const base = rates.find((item) => item.base) ?? rates[0]

  /** Валюты, которые уже встречаются в открытых счетах пользователя */
  const usedCurrencies = useMemo(() => {
    const codes = new Set<string>()
    accounts.forEach((account) => {
      if (!account.archived) codes.add(account.currency)
    })
    return codes
  }, [accounts])

  /** Справочник валют: активные сверху, остальные ниже приглушённые */
  const { active, inactive } = useMemo(() => {
    const activeList: CurrencyRate[] = []
    const inactiveList: CurrencyRate[] = []
    for (const rate of rates) {
      if (rate.base || usedCurrencies.has(rate.code)) {
        activeList.push(rate)
      } else {
        inactiveList.push(rate)
      }
    }
    return { active: activeList, inactive: inactiveList }
  }, [rates, usedCurrencies])

  const openEdit = (rate: CurrencyRate) => {
    setDraft(rate)
    // Курс в справочнике — «сколько валюты за 1 базовую», его и редактируем
    setValue(String(rate.rate).replace('.', ','))
  }

  const saveRate = async () => {
    if (!draft) return
    const parsed = Number(value.replace(',', '.'))
    if (!Number.isFinite(parsed) || parsed <= 0) {
      toast({ title: t('currencies.customSaved'), description: t('recordForm.amountInvalid'), tone: 'error' })
      return
    }
    setPending(true)
    try {
      await setUserRate(draft.code, parsed)
      toast({ title: t('currencies.customSaved'), description: `${draft.code} = ${parsed}`, tone: 'success' })
      setDraft(null)
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

  const resetRate = async (rate: CurrencyRate) => {
    setPending(true)
    try {
      await resetUserRate(rate.code)
      toast({ title: t('currencies.customReset'), description: rate.code, tone: 'info' })
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

  return (
    <SettingsLayout title={t('settings.currencies')} subtitle={t('settings.currencies.rate')}>
      {!multiCurrency && (
        <Card className="mb-4 border-l-2 border-l-[var(--accent)]">
          <div className="flex flex-wrap items-center gap-3">
            <span className="grid size-9 place-items-center rounded-md bg-accent-soft text-accent-on-soft">
              <Sparkles className="size-4" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <h2 className="text-label font-semibold text-fg-primary">{t('currencies.premiumTitle')}</h2>
              <p className="text-caption text-fg-secondary">{t('currencies.premiumText')}</p>
            </div>
            <Button variant="subtle" size="sm" className="ml-auto" onClick={() => navigate('/settings/payments')}>
              {t('currencies.premiumCta')}
            </Button>
          </div>
        </Card>
      )}

      <Card className="overflow-hidden p-0">
        <div className="flex flex-wrap items-baseline justify-between gap-2 border-b border-stroke-subtle px-4 py-2.5">
          <h2 className="text-label font-semibold text-fg-primary">{t('settings.currencies.yours')}</h2>
          {base && (
            <p className="text-caption text-fg-tertiary">
              {t('currencies.base')}: {base.code}
            </p>
          )}
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-label">
            <caption className="sr-only">{t('settings.currencies.yours')}</caption>
            <thead>
              <tr>
                <th
                  scope="col"
                  className="px-3 py-2 text-left text-caption uppercase tracking-wide text-fg-tertiary sm:px-4"
                >
                  {t('currencies.name')}
                </th>
                <th
                  scope="col"
                  className="px-3 py-2 text-left text-caption uppercase tracking-wide text-fg-tertiary sm:px-4"
                >
                  {t('currencies.rate')}
                </th>
                <th
                  scope="col"
                  className="px-4 py-2 text-right text-caption uppercase tracking-wide text-fg-tertiary"
                >
                  <span className="sr-only">{t('accounts.rowMenu')}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rates.length === 0 && (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-caption text-fg-tertiary">
                    {t('state.empty')}
                  </td>
                </tr>
              )}
              {/* Сначала активные валюты (в счетах пользователя) */}
              {active.map((item, index) => (
                <tr key={item.code} className={index > 0 ? 'border-t border-stroke-subtle' : undefined}>
                  <th scope="row" className="px-3 py-2.5 text-left font-normal sm:px-4">
                    <span className="flex items-center gap-2">
                      <span className="grid size-7 place-items-center rounded-pill bg-surface-2 text-caption font-semibold text-fg-primary">
                        {item.code.slice(0, 2)}
                      </span>
                      <span className="min-w-0">
                        <span className="block text-label font-medium text-fg-primary">
                          {item.code} · {item.name}
                        </span>
                        <span className="flex flex-wrap items-center gap-1.5 text-caption text-fg-tertiary">
                          {item.base && <span>{t('currencies.base')}</span>}
                          {item.custom && (
                            <span className="rounded-xs bg-accent-soft px-1.5 py-0.5 text-accent-on-soft">
                              {t('currencies.customRate')}
                            </span>
                          )}
                          {usedCurrencies.has(item.code) && !item.base && (
                            <span className="text-[10px] uppercase tracking-wide text-fg-tertiary">
                              {t('currencies.inUse')}
                            </span>
                          )}
                        </span>
                      </span>
                    </span>
                  </th>
                  <td className="px-3 py-2.5 text-fg-secondary sm:px-4">
                    {item.base ? (
                      <span className="text-caption text-fg-tertiary">—</span>
                    ) : (
                      <span className="flex flex-wrap gap-x-3 gap-y-0.5 text-caption">
                        <span>
                          {t('currencies.rateHint', {
                            base: base?.code ?? '',
                            rate: item.rate.toFixed(4),
                            code: item.code,
                          })}
                        </span>
                        <span className="text-fg-tertiary">
                          1 {item.code} = {(1 / item.rate).toFixed(3)} {base?.code ?? ''}
                        </span>
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2.5 sm:px-4">
                    {!item.base && (
                      <div className="flex justify-end gap-1">
                        {!multiCurrency && (
                          <Lock
                            className="size-3.5 text-fg-tertiary"
                            aria-label={t('currencies.premiumTitle')}
                          />
                        )}
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={t('currencies.setCustom')}
                          title={multiCurrency ? t('currencies.setCustom') : t('currencies.premiumTitle')}
                          disabled={!multiCurrency}
                          onClick={() => openEdit(item)}
                        >
                          <Pencil className="size-3.5 text-accent" aria-hidden="true" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={t('currencies.resetCustom')}
                          title={multiCurrency ? t('currencies.resetCustom') : t('currencies.premiumTitle')}
                          disabled={!multiCurrency || !item.custom || pending}
                          onClick={() => void resetRate(item)}
                        >
                          <RotateCcw className="size-3.5 text-fg-tertiary" aria-hidden="true" />
                        </Button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
              {/* Неактивные валюты справочника — приглушённым тоном */}
              {inactive.length > 0 && (
                <>
                  {active.length > 0 && (
                    <tr>
                      <td
                        colSpan={3}
                        className="px-4 py-3 text-caption text-fg-tertiary"
                      >
                        {t('currencies.available')}
                      </td>
                    </tr>
                  )}
                  {inactive.map((item) => (
                    <tr key={item.code} className="border-t border-stroke-subtle opacity-50 transition-opacity hover:opacity-75">
                      <th scope="row" className="px-3 py-2.5 text-left font-normal sm:px-4">
                        <span className="flex items-center gap-2">
                          <span className="grid size-7 place-items-center rounded-pill bg-surface-2 text-caption font-semibold text-fg-tertiary">
                            {item.code.slice(0, 2)}
                          </span>
                          <span className="min-w-0">
                            <span className="block text-label font-medium text-fg-secondary">
                              {item.code} · {item.name}
                            </span>
                          </span>
                        </span>
                      </th>
                      <td className="px-3 py-2.5 text-fg-tertiary sm:px-4">
                        <span className="flex flex-wrap gap-x-3 gap-y-0.5 text-caption">
                          <span>
                            {t('currencies.rateHint', {
                              base: base?.code ?? '',
                              rate: item.rate.toFixed(4),
                              code: item.code,
                            })}
                          </span>
                          <span className="text-fg-tertiary">
                            1 {item.code} = {(1 / item.rate).toFixed(3)} {base?.code ?? ''}
                          </span>
                        </span>
                      </td>
                      <td className="px-3 py-2.5 sm:px-4">
                        <div className="flex justify-end gap-1">
                          {!multiCurrency && (
                            <Lock
                              className="size-3.5 text-fg-tertiary"
                              aria-label={t('currencies.premiumTitle')}
                            />
                          )}
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            aria-label={t('currencies.setCustom')}
                            title={multiCurrency ? t('currencies.setCustom') : t('currencies.premiumTitle')}
                            disabled={!multiCurrency}
                            onClick={() => openEdit(item)}
                          >
                            <Pencil className="size-3.5 text-accent" aria-hidden="true" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <Dialog open={Boolean(draft)} onOpenChange={(next) => !next && setDraft(null)}>
        <DialogContent
          title={t('currencies.setCustom')}
          description={draft ? `${draft.code} · ${draft.name}` : undefined}
          footer={
            <div className="flex justify-end gap-2">
              <Button variant="subtle" onClick={() => setDraft(null)}>
                {t('common.cancel')}
              </Button>
              <Button onClick={() => void saveRate()} disabled={pending}>
                {pending ? t('state.saving') : t('common.save')}
              </Button>
            </div>
          }
        >
          {draft && (
            <div className="space-y-3">
              <Field
                label={`${t('currencies.rate')} (${base?.code ?? ''})`}
                hint={t('currencies.rateHint', {
                  base: base?.code ?? '',
                  rate: value || '…',
                  code: draft.code,
                })}
              >
                <Input value={value} onChange={(event) => setValue(event.target.value)} inputMode="decimal" autoFocus />
              </Field>
              <Field label={t('accounts.currency')}>
                <Input value={`${draft.code} · ${draft.name}`} readOnly disabled />
              </Field>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </SettingsLayout>
  )
}
