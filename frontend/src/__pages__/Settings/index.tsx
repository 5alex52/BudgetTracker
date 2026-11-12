import { useEffect, useState } from 'react'
import { Bell, BellRing, CalendarDays, Languages, Send, Wallet } from 'lucide-react'
import { useI18n } from '@/i18n'
import { ApiError, usersApi } from '@/api'
import type { TelegramLinkDto } from '@/api/types'
import { useAuthStore } from '@/store/auth'
import { useFinanceStore } from '@/store/finance'
import { SettingsLayout } from '@/components/settings/SettingsLayout'
import { Card, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { FilterSelect } from '@/components/ui/overlays'
import { useToast } from '@/components/ui/toast'

/**
 * «Настройки»: профиль, оформление, язык и базовая валюта.
 *
 * Профиль пишется на сервер через `PATCH /users/me`; язык дублируется
 * в профиле, чтобы настройки переезжали между устройствами, но интерфейс
 * реагирует мгновенно — локально, без ожидания ответа.
 * Тема выбирается только в выпадающем меню пользователя, а базовая валюта —
 * только в блоке «Внешний вид»: в форме профиля она была продублирована.
 */
export function SettingsPage() {
  const { t, locale, setLocale } = useI18n()
  const { toast } = useToast()

  const user = useAuthStore((state) => state.user)
  const setUser = useAuthStore((state) => state.setUser)
  const baseCurrency = useFinanceStore((state) => state.baseCurrency)
  const rates = useFinanceStore((state) => state.rates)

  const [firstname, setFirstname] = useState('')
  const [lastname, setLastname] = useState('')
  const [email, setEmail] = useState('')
  const [currency, setCurrency] = useState(baseCurrency)
  const [period, setPeriod] = useState<'day' | 'week' | 'month'>('month')
  const [pending, setPending] = useState(false)
  const [remind, setRemind] = useState<'0' | '1' | '2'>('1')
  const [pushOn, setPushOn] = useState(
    () =>
      typeof Notification !== 'undefined' &&
      localStorage.getItem('bt-push-endpoint') !== null &&
      Notification.permission === 'granted',
  )
  const [pushBusy, setPushBusy] = useState(false)
  const [telegramLink, setTelegramLink] = useState<TelegramLinkDto | null>(null)

  /* Профиль приходит асинхронно: заполняем форму, когда он появился */
  useEffect(() => {
    if (!user) return
    setFirstname(user.firstname ?? '')
    setLastname(user.lastname ?? '')
    setEmail(user.email)
  }, [user])

  useEffect(() => setCurrency(baseCurrency), [baseCurrency])

  useEffect(() => {
    const saved = user?.default_period
    if (saved === 'day' || saved === 'week' || saved === 'month') setPeriod(saved)
  }, [user])

  useEffect(() => {
    const saved = user?.reminder_days_before
    if (saved === 0 || saved === 1 || saved === 2) setRemind(String(saved) as '0' | '1' | '2')
  }, [user])

  const save = async () => {
    setPending(true)
    try {
      const updated = await usersApi.updateProfile({
        firstname: firstname.trim(),
        lastname: lastname.trim(),
        email: email.trim(),
      })
      setUser(updated)
      toast({ title: t('profile.saved'), tone: 'success' })
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

  /* Базовая валюта из блока «Внешний вид» сохраняется сразу: без кнопки «Обновить» */
  const changeCurrency = async (next: string) => {
    if (next === currency) return
    setCurrency(next)
    try {
      const updated = await usersApi.updateProfile({ base_currency: next })
      setUser(updated)
      // От базовой валюты зависят суммы в аналитике — перечитываем курсы
      await useFinanceStore.getState().reloadRates()
      toast({ title: t('profile.saved'), tone: 'success' })
    } catch (caught) {
      setCurrency(baseCurrency)
      toast({
        title: t('profile.saveFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    }
  }

  /* Базовый период тоже сохраняется сразу: от него зависят «Обзор» и «Аналитика» */
  const changePeriod = async (next: 'day' | 'week' | 'month') => {
    if (next === period) return
    setPeriod(next)
    try {
      const updated = await usersApi.updateProfile({ default_period: next })
      setUser(updated)
      toast({ title: t('profile.saved'), tone: 'success' })
    } catch (caught) {
      toast({
        title: t('profile.saveFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    }
  }

  /* Напоминания о подписках: за сколько дней предупреждать (сохраняется сразу) */
  const changeRemind = async (next: '0' | '1' | '2') => {
    if (next === remind) return
    setRemind(next)
    try {
      const updated = await usersApi.updateProfile({ reminder_days_before: Number(next) })
      setUser(updated)
      toast({ title: t('profile.saved'), tone: 'success' })
    } catch (caught) {
      setRemind(String(user?.reminder_days_before ?? 1) as '0' | '1' | '2')
      toast({
        title: t('profile.saveFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    }
  }

  const pushSupported =
    window.isSecureContext &&
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    typeof Notification !== 'undefined'

  const togglePush = async () => {
    setPushBusy(true)
    try {
      if (pushOn) {
        const registration = await navigator.serviceWorker.ready
        const subscription = await registration.pushManager.getSubscription()
        const endpoint = localStorage.getItem('bt-push-endpoint') ?? subscription?.endpoint
        if (subscription) await subscription.unsubscribe()
        if (endpoint) await usersApi.unsubscribePush(endpoint)
        localStorage.removeItem('bt-push-endpoint')
        setPushOn(false)
        toast({ title: t('settings.pushOff'), tone: 'info' })
      } else {
        const permission = await Notification.requestPermission()
        if (permission !== 'granted') {
          toast({ title: t('settings.pushBlocked'), tone: 'error' })
          return
        }
        const { public_key } = await usersApi.getPushPublicKey()
        const registration = await navigator.serviceWorker.ready
        const subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(public_key),
        })
        const keys = subscription.toJSON().keys
        if (!keys?.p256dh || !keys?.auth) throw new Error('Push keys missing')
        await usersApi.subscribePush({
          endpoint: subscription.endpoint,
          keys: { p256dh: keys.p256dh, auth: keys.auth },
        })
        localStorage.setItem('bt-push-endpoint', subscription.endpoint)
        setPushOn(true)
        toast({ title: t('settings.pushOn'), tone: 'success' })
      }
    } catch (caught) {
      toast({
        title: t('settings.pushFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    } finally {
      setPushBusy(false)
    }
  }

  const connectTelegram = async () => {
    try {
      const link = await usersApi.getTelegramLink()
      setTelegramLink(link)
      if (link.deep_link) window.open(link.deep_link, '_blank', 'noopener')
    } catch (caught) {
      toast({
        title: t('settings.pushFailed'),
        description: caught instanceof ApiError ? caught.detail : String(caught),
        tone: 'error',
      })
    }
  }

  /* Привязка подтверждается ботом асинхронно: «Проверить» перечитывает профиль */
  const checkTelegram = async () => {
    const updated = await usersApi.getProfile()
    setUser(updated)
    if (updated.telegram_id) {
      setTelegramLink(null)
      toast({ title: t('settings.telegramLinked'), tone: 'success' })
    } else {
      toast({ title: t('settings.telegramNotLinked'), tone: 'info' })
    }
  }

  const disconnectTelegram = async () => {
    await usersApi.unlinkTelegram()
    setUser(await usersApi.getProfile())
    setTelegramLink(null)
    toast({ title: t('settings.telegramUnlinked'), tone: 'info' })
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
                  onValueChange={(next) => void changeCurrency(next)}
                  // В закрытом селекте — только код: полное «код · название» не
                  // помещается в узкий триггер и обрезается. Список остаётся полным.
                  renderValue={currency}
                  options={rates.map((rate) => ({
                    value: rate.code,
                    label: `${rate.code} · ${rate.name}`,
                  }))}
                />
              </div>
            </SettingRow>

            <SettingRow label={t('settings.defaultPeriod')} icon={<CalendarDays className="size-4" />}>
              <div className="w-44">
                <FilterSelect
                  ariaLabel={t('settings.defaultPeriod')}
                  value={period}
                  onValueChange={(value) => void changePeriod(value as 'day' | 'week' | 'month')}
                  options={[
                    { value: 'day', label: t('settings.periodDay') },
                    { value: 'week', label: t('settings.periodWeek') },
                    { value: 'month', label: t('settings.periodMonth') },
                  ]}
                />
              </div>
            </SettingRow>
          </div>
        </Card>

        <Card>
          <CardHeader title={t('settings.notifications')} subtitle={t('settings.notificationsHint')} />
          <div className="mt-4 space-y-4">
            <SettingRow label={t('settings.remindBefore')} icon={<BellRing className="size-4" />}>
              <div className="w-44">
                <FilterSelect
                  ariaLabel={t('settings.remindBefore')}
                  value={remind}
                  onValueChange={(value) => void changeRemind(value as '0' | '1' | '2')}
                  options={[
                    { value: '2', label: t('settings.remind2days') },
                    { value: '1', label: t('settings.remind1day') },
                    { value: '0', label: t('settings.remindSameDay') },
                  ]}
                />
              </div>
            </SettingRow>

            <SettingRow
              label={t('settings.push')}
              icon={<Bell className="size-4" />}
              hint={t('settings.pushHint')}
            >
              {pushSupported ? (
                <Button variant="subtle" size="sm" disabled={pushBusy} onClick={() => void togglePush()}>
                  {pushOn ? t('settings.pushDisable') : t('settings.pushEnable')}
                </Button>
              ) : (
                <span className="text-caption text-fg-tertiary">{t('settings.pushUnsupported')}</span>
              )}
            </SettingRow>

            <SettingRow
              label={t('settings.telegram')}
              icon={<Send className="size-4" />}
              hint={telegramLink ? t('settings.telegramOpen') : t('settings.telegramHint')}
            >
              {user?.telegram_id ? (
                <div className="flex items-center gap-2">
                  <span className="text-caption text-fg-tertiary">{t('settings.telegramLinked')}</span>
                  <Button variant="subtle" size="sm" onClick={() => void disconnectTelegram()}>
                    {t('settings.telegramUnlink')}
                  </Button>
                </div>
              ) : telegramLink ? (
                <div className="flex items-center gap-2">
                  <code className="rounded-xs bg-surface-2 px-2 py-1 text-caption" title={t('settings.telegramCode')}>
                    /start {telegramLink.code}
                  </code>
                  <Button variant="subtle" size="sm" onClick={() => void checkTelegram()}>
                    {t('settings.telegramCheck')}
                  </Button>
                </div>
              ) : (
                <Button variant="subtle" size="sm" onClick={() => void connectTelegram()}>
                  {t('settings.telegramConnect')}
                </Button>
              )}
            </SettingRow>
          </div>
        </Card>
      </div>
    </SettingsLayout>
  )
}

/** VAPID-ключ приходит base64url — PushManager ждёт байты. */
function urlBase64ToUint8Array(base64: string): Uint8Array<ArrayBuffer> {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4)
  const normalized = (base64 + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = window.atob(normalized)
  const bytes = new Uint8Array(raw.length)
  for (let index = 0; index < raw.length; index += 1) bytes[index] = raw.charCodeAt(index)
  return bytes
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
