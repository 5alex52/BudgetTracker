import { useState } from 'react'
import { Languages, Palette, Shield, SlidersHorizontal, Trash2 } from 'lucide-react'
import { useI18n } from '@/i18n'
import { useTheme, type ThemeMode } from '@/hooks/useTheme'
import { SettingsLayout } from '@/components/settings/SettingsLayout'
import { Card, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { SegmentedControl, Switch } from '@/components/ui/toggles'
import { FilterSelect } from '@/components/ui/overlays'
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialogs'
import { useToast } from '@/components/ui/toast'


/**
 * «Настройки»: две группы навигации (WALLET / ОБЩИЕ), форма профиля
 * и общие предпочтения. Всё состояние локальное — бизнес-логика не затрагивается.
 */
export function SettingsPage() {
  const { t, locale, setLocale } = useI18n()
  const { mode, setMode } = useTheme()
  const { toast } = useToast()

  const [firstName, setFirstName] = useState('Алексей')
  const [lastName, setLastName] = useState('Курковский')
  const [email, setEmail] = useState('alexey.kurkovsky@example.com')
  const [hideDecimals, setHideDecimals] = useState(false)
  const [autoLogout, setAutoLogout] = useState(false)
  const [interval, setInterval] = useState('thisMonth')

  return (
    <SettingsLayout
      title={t('settings.title')}
      subtitle={t('settings.profile')}
    >
      <div className="space-y-4">
        <Card id="general">
          <CardHeader title={t('settings.profile')} subtitle={t('settings.general')} />
          <form
            className="mt-4 grid gap-3 sm:grid-cols-2"
            onSubmit={(event) => {
              event.preventDefault()
              toast({ title: t('settings.update'), tone: 'success' })
            }}
          >
            <Field label={t('settings.firstName')}>
              <Input value={firstName} onChange={(event) => setFirstName(event.target.value)} />
            </Field>
            <Field label={t('settings.lastName')}>
              <Input value={lastName} onChange={(event) => setLastName(event.target.value)} />
            </Field>
            <Field label={t('settings.email')} className="sm:col-span-2">
              <Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
            </Field>
            <div className="sm:col-span-2">
              <Button type="submit">{t('settings.update')}</Button>
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
                onValueChange={(value) => setMode(value as ThemeMode)}
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
                  onValueChange={(value) => setLocale(value as 'ru' | 'en')}
                  options={[
                    { value: 'ru', label: 'Русский' },
                    { value: 'en', label: 'English' },
                  ]}
                />
              </div>
            </SettingRow>

            <SettingRow label={t('settings.dashboardInterval')} icon={<SlidersHorizontal className="size-4" />}>
              <div className="w-44">
                <FilterSelect
                  ariaLabel={t('settings.dashboardInterval')}
                  value={interval}
                  onValueChange={setInterval}
                  options={[
                    { value: 'thisMonth', label: t('settings.interval.thisMonth') },
                    { value: 'prevMonth', label: t('dashboard.monthPrev') },
                  ]}
                />
              </div>
            </SettingRow>

            <SettingRow label={t('settings.numberFormat')} icon={<SlidersHorizontal className="size-4" />}>
              <Switch checked={hideDecimals} onCheckedChange={setHideDecimals} label={t('settings.hideDecimals')} />
            </SettingRow>

            <SettingRow label={t('settings.autoLogout')} icon={<Shield className="size-4" />} hint={t('settings.autoLogoutHint')}>
              <Switch checked={autoLogout} onCheckedChange={setAutoLogout} label={t('settings.autoLogout')} />
            </SettingRow>
          </div>
        </Card>

        <Card>
          <CardHeader title={t('settings.privacy')} subtitle={t('settings.deleteLocalHint')} />
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <p className="max-w-md text-label text-fg-secondary">{t('settings.deleteLocalHint')}</p>
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="danger" className="gap-1.5">
                  <Trash2 className="size-4" aria-hidden="true" />
                  {t('settings.deleteLocalAction')}
                </Button>
              </DialogTrigger>
              <DialogContent title={t('settings.deleteLocal')} description={t('settings.deleteLocalHint')}>
                <div className="mt-6 flex justify-end gap-2">
                  <Button variant="subtle">{t('common.cancel')}</Button>
                  <Button variant="danger">{t('settings.deleteLocalAction')}</Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </Card>
      </div>
    </SettingsLayout>
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
