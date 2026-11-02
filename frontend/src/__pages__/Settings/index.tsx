import { useEffect, useState } from 'react'
import { Languages, Palette, SlidersHorizontal, Wallet } from 'lucide-react'
import { useI18n } from '@/i18n'
import { useTheme, type ThemeMode } from '@/hooks/useTheme'
import { ApiError, usersApi } from '@/api'
import { useAuthStore } from '@/store/auth'
import { useFinanceStore } from '@/store/finance'
import { SettingsLayout } from '@/components/settings/SettingsLayout'
import { Card, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { SegmentedControl, Switch } from '@/components/ui/toggles'
import { FilterSelect } from '@/components/ui/overlays'
import { useToast } from '@/components/ui/toast'

/**
 * «Настройки»: профиль, оформление, язык и базовая валюта.
 *
 * Профиль пишется на сервер через `PATCH /users/me`; тема и язык дублируются
 * в профиле, чтобы настройки переезжали между устройствами, но интерфейс
 * реагирует мгновенно — локально, без ожидания ответа.
 */
export function SettingsPage() {
  const { t, locale, setLocale } = useI18n()
  const { mode, setMode } = useTheme()
  const { toast } = useToast()

  const user = useAuthStore((state) => state.user)
  const setUser = useAuthStore((state) => state.setUser)
  const baseCurrency = useFinanceStore((state) => state.baseCurrency)
  const rates = useFinanceStore((state) => state.rates)

  const [firstname, setFirstname] = useState('')
  const [lastname, setLastname] = useState('')
  const [email, setEmail] = useState('')
  const [currency, setCurrency] = useState(baseCurrency)
  const [pending, setPending] = useState(false)

  /* Профиль приходит асинхронно: заполняем форму, когда он появился */
  useEffect(() => {
    if (!user) return
    setFirstname(user.firstname ?? '')
    setLastname(user.lastname ?? '')
    setEmail(user.email)
  }, [user])

  useEffect(() => setCurrency(baseCurrency), [baseCurrency])

  const save = async () => {
    setPending(true)
    try {
      const updated = await usersApi.updateProfile({
        firstname: firstname.trim(),
        lastname: lastname.trim(),
        email: email.trim(),
        base_currency: currency,
      })
      setUser(updated)
      toast({ title: t('profile.saved'), tone: 'success' })
      // Базовая валюта влияет на суммы в аналитике — перечитываем курсы
      await useFinanceStore.getState().reloadRates()
    } catch (caught) {
      toast({
        title: t('profile.saveFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    } finally {
      setPending(false)
    }
  }

  const changeLocale = (next: 'ru' | 'en') => {
    setLocale(next)
    void usersApi.updateProfile({ locale: next }).catch(() => undefined)
  }

  const changeTheme = (next: ThemeMode) => {
    setMode(next)
    void usersApi.updateProfile({ theme: next }).catch(() => undefined)
  }

  return (
    <SettingsLayout title={t('settings.title')} subtitle={t('settings.profile')}>
      <div className="space-y-4">
        <Card id="general">
          <CardHeader title={t('settings.profile')} subtitle={t('settings.general')} />
          <form
            className="mt-4 grid gap-3 sm:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault()
              void save()
            }}
          >
            <Field label={t('settings.firstName')}>
              <Input value={firstname} onChange={(event) => setFirstname(event.target.value)} />
            </Field>
            <Field label={t('settings.lastName')}>
              <Input value={lastname} onChange={(event) => setLastname(event.target.value)} />
            </Field>
            <Field label={t('settings.email')} className="sm:col-span-2">
              <Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
            </Field>
            <Field label={t('profile.baseCurrency')} hint={t('settings.baseCurrencyHint')}>
              <FilterSelect
                ariaLabel={t('profile.baseCurrency')}
                value={currency}
                onValueChange={setCurrency}
                options={rates.map((rate) => ({
                  value: rate.code,
                  label: `${rate.code} · ${rate.name}`,
                }))}
              />
            </Field>
            <div className="flex items-end sm:col-span-2">
              <Button type="submit" disabled={pending || !email.trim()}>
                {pending ? t('state.saving') : t('settings.update')}
              </Button>
            </div>
          </form>
        </Card>

        <Card>
          <CardHeader title={t('settings.appearance')} subtitle={t('settings.language')} />
          <div className="mt-4 space-y-4">
            <SettingRow label={t('settings.appearance')} icon={<Palette className="size-4" />}>
              <SegmentedControl
                className="[&>*]:px-2.5 [&>*]:text-caption sm:[&>*]:px-3 sm:[&>*]:text-label"
                aria-label={t('settings.appearance')}
                value={mode}
                onValueChange={(value) => changeTheme(value as ThemeMode)}
                items={[
                  { value: 'system', label: t('settings.appearance.system') },
                  { value: 'light', label: t('settings.appearance.light') },
                  { value: 'dark', label: t('settings.appearance.dark') },
                ]}
              />
            </SettingRow>

            <SettingRow label={t('settings.language')} icon={<Languages className="size-4" />}>
              <div className="w-44">
                <FilterSelect
                  ariaLabel={t('settings.language')}
                  value={locale}
                  onValueChange={(value) => changeLocale(value as 'ru' | 'en')}
                  options={[
                    { value: 'ru', label: 'Русский' },
                    { value: 'en', label: 'English' },
                  ]}
                />
              </div>
            </SettingRow>

            <SettingRow label={t('profile.baseCurrency')} icon={<Wallet className="size-4" />}>
              <div className="w-44">
                <FilterSelect
                  ariaLabel={t('profile.baseCurrency')}
                  value={currency}
                  onValueChange={setCurrency}
                  options={rates.map((rate) => ({ value: rate.code, label: rate.code }))}
                />
              </div>
            </SettingRow>

            <SettingRow
              label={t('settings.numberFormat')}
              icon={<SlidersHorizontal className="size-4" />}
            >
              <HideDecimalsSwitch />
            </SettingRow>
          </div>
        </Card>
      </div>
    </SettingsLayout>
  )
}

/** «Скрывать копейки» — клиентская настройка отображения, живёт в localStorage. */
function HideDecimalsSwitch() {
  const { t } = useI18n()
  const key = 'bt-hide-decimals'
  const [hide, setHide] = useState(() => localStorage.getItem(key) === '1')

  return (
    <Switch
      checked={hide}
      onCheckedChange={(next) => {
        setHide(next)
        localStorage.setItem(key, next ? '1' : '0')
      }}
      label={t('settings.hideDecimals')}
    />
  )
}

function SettingRow({
  label,
  icon,
  hint,
  children,
}: {
  label: string
  icon: React.ReactNode
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 border-t border-stroke-subtle pt-3 first:border-0 first:pt-0">
      <div className="min-w-0 flex-1 basis-40">
        <p className="flex items-center gap-2 text-label font-medium text-fg-primary">
          <span className="text-fg-tertiary" aria-hidden="true">
            {icon}
          </span>
          {label}
        </p>
        {hint && <p className="mt-0.5 max-w-md text-caption text-fg-tertiary">{hint}</p>}
      </div>
      {/* Контрол не сжимается сам и на узком экране занимает всю ширину */}
      <div className="min-w-0 shrink-0 basis-auto max-w-full [&_[role=group]]:max-w-full">{children}</div>
    </div>
  )
}
