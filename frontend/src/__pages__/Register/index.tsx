import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, ShieldCheck } from 'lucide-react'
import { useI18n } from '@/i18n'
import { useAuthStore } from '@/store/auth'
import { authApi } from '@/api'
import { ApiError } from '@/api/client'
import { Wordmark } from '@/components/brand/Logo'
import { GlassBackdrop } from '@/components/glass/GlassBackdrop'
import { GlassSurface } from '@/components/glass/GlassSurface'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { useToast } from '@/components/ui/toast'
import { LanguageSwitcher, ThemeSwitcher } from '@/components/layout/Switchers'

/** Минимальная длина пароля: та же проверка, что и на сервере. */
const MIN_PASSWORD = 8

/**
 * «Регистрация»: тот же каркас, что у входа.
 *
 * После успешного создания аккаунта сразу выполняем вход — пользователь не
 * должен вводить пароль дважды. Если пришли со страницы тарифов, возвращаем
 * в оплату, чтобы выбранный план не потерялся.
 */
export function RegisterPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const { toast } = useToast()
  const signIn = useAuthStore((state) => state.signIn)

  const [firstname, setFirstname] = useState('')
  const [lastname, setLastname] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const wantsPlan = new URLSearchParams(window.location.search).get('plan')

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (password.length < MIN_PASSWORD) {
      setError(t('register.shortPassword', { count: MIN_PASSWORD }))
      return
    }
    setPending(true)
    setError(null)
    try {
      await authApi.register({
        firstname: firstname.trim(),
        lastname: lastname.trim(),
        email: email.trim(),
        password,
      })
      await signIn(email.trim(), password)
      toast({ title: t('register.done'), tone: 'success' })
      navigate(wantsPlan ? '/settings/payments' : '/', { replace: true })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.detail : String(caught))
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="relative min-h-dvh">
      <GlassBackdrop />

      <div className="relative z-[1] mx-auto flex min-h-dvh w-full max-w-container flex-col gap-6 px-4 py-6 md:px-6">
        <header className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <Link to="/" className="rounded-sm focus-visible:outline-none">
            <Wordmark />
          </Link>
          <div className="flex w-full flex-col items-stretch gap-2 sm:w-auto sm:flex-row sm:items-center">
            <LanguageSwitcher />
            <ThemeSwitcher stretch />
          </div>
        </header>

        <div className="grid flex-1 items-center gap-8 pb-6 lg:grid-cols-[1.15fr_minmax(380px,460px)]">
          <section className="order-2 lg:order-1">
            <h1 className="max-w-xl text-display font-semibold tracking-tight text-fg-primary">
              {t('register.headline')}
            </h1>
            <p className="mt-3 max-w-xl text-body leading-relaxed text-fg-secondary">{t('register.subline')}</p>
            <Link
              to="/features"
              className="mt-3 inline-flex items-center gap-1.5 rounded-xs text-label font-medium text-accent hover:underline"
            >
              {t('login.learnMore')}
              <ArrowRight className="size-4" aria-hidden="true" />
            </Link>

            <div className="mt-8 max-w-xl">
              <GlassSurface level="md" className="p-4">
                <p className="flex items-center gap-1.5 text-caption text-fg-tertiary">
                  <ShieldCheck className="size-3.5" aria-hidden="true" />
                  {t('register.legal')}
                </p>
              </GlassSurface>
            </div>
          </section>

          <section className="order-1 lg:order-2">
            <GlassSurface level="lg" className="p-6">
              <h2 className="text-title font-semibold text-fg-primary">{t('register.title')}</h2>

              <form onSubmit={submit} className="mt-4 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <Field label={t('register.firstname')}>
                    <Input
                      value={firstname}
                      onChange={(event) => setFirstname(event.target.value)}
                      placeholder={t('register.firstnamePlaceholder')}
                      autoComplete="given-name"
                      required
                    />
                  </Field>
                  <Field label={t('register.lastname')}>
                    <Input
                      value={lastname}
                      onChange={(event) => setLastname(event.target.value)}
                      placeholder={t('register.lastnamePlaceholder')}
                      autoComplete="family-name"
                      required
                    />
                  </Field>
                </div>

                <Field label={t('login.email')}>
                  <Input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder={t('login.emailPlaceholder')}
                    autoComplete="email"
                    required
                  />
                </Field>

                <Field
                  label={t('login.password')}
                  error={error ?? undefined}
                  hint={error ? undefined : t('register.passwordHint', { count: MIN_PASSWORD })}
                >
                  <Input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder={t('register.passwordPlaceholder')}
                    autoComplete="new-password"
                    invalid={Boolean(error)}
                    required
                  />
                </Field>

                <Button type="submit" block disabled={pending}>
                  {pending ? t('state.loading') : t('register.submit')}
                </Button>
              </form>

              <p className="mt-3 text-caption text-fg-tertiary">
                {t('register.haveAccount')}{' '}
                <Link to="/login" className="font-medium text-accent hover:underline">
                  {t('register.signIn')}
                </Link>
              </p>
            </GlassSurface>
          </section>
        </div>
      </div>
    </div>
  )
}
