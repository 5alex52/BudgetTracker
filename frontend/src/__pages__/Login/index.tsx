import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRight, ShieldCheck } from 'lucide-react'
import { useI18n } from '@/i18n'
import { useAuthStore } from '@/store/auth'
import { ADMIN_CREDENTIALS, DEMO_CREDENTIALS, DEMO_HINT_ENABLED } from '@/__shared__/constants/demo'
import { oauthStartUrl } from '@/api/auth'
import { Wordmark } from '@/components/brand/Logo'
import { GlassBackdrop } from '@/components/glass/GlassBackdrop'
import { GlassSurface } from '@/components/glass/GlassSurface'
import { Button } from '@/components/ui/button'
import { Field, Input } from '@/components/ui/field'
import { useToast } from '@/components/ui/toast'
import { LanguageSwitcher, ThemeSwitcher } from '@/components/layout/Switchers'

/** Куда вернуть пользователя после входа: путь, с которого его увели на /login. */
function useRedirectTarget(): string {
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from
  return from && !from.startsWith('/login') ? from : '/'
}

/**
 * «Окно входа»: слева промо-часть и мобильное приложение, справа форма.
 * На 390 px панели складываются в столбик, промо уходит вниз как второстепенное.
 *
 * Форма работает с настоящим backend: `POST /api/auth/login` кладёт токен в
 * httpOnly-cookie, после чего приложение переходит на запрошенный экран.
 */
export function LoginPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const redirectTo = useRedirectTarget()
  const { toast } = useToast()
  const signIn = useAuthStore((state) => state.signIn)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Внешний вход: уводим браузер на backend, тот редиректит к провайдеру.
   * Если ключи на сервере не заданы — ответит 503, показываем понятный тост
   * вместо «битой» страницы.
   */
  const startOAuth = async (provider: 'github') => {
    try {
      const response = await fetch(oauthStartUrl(provider), { redirect: 'manual' })
      if (response.status === 503) {
        toast({ title: t('login.oauthUnavailable', { provider }), tone: 'info' })
        return
      }
      window.location.href = oauthStartUrl(provider)
    } catch {
      toast({ title: t('login.oauthUnavailable', { provider }), tone: 'info' })
    }
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setPending(true)
    setError(null)
    try {
      await signIn(email, password)
      navigate(redirectTo, { replace: true })
    } catch {
      setError(t('login.error'))
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
          {/* На 390 px пара переключателей шире строки: в столбик на всю ширину */}
          <div className="flex w-full flex-col items-stretch gap-2 sm:w-auto sm:flex-row sm:items-center">
            <LanguageSwitcher />
            <ThemeSwitcher stretch />
          </div>
        </header>

        <div className="grid flex-1 items-center gap-8 pb-6 lg:grid-cols-[1.15fr_minmax(380px,460px)]">
          {/* Промо */}
          <section className="order-2 lg:order-1">
            <h1 className="max-w-xl text-display font-semibold tracking-tight text-fg-primary">
              {t('login.headline')}
            </h1>
            <p className="mt-3 max-w-xl text-body leading-relaxed text-fg-secondary">{t('login.subline')}</p>
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
                  {t('login.legal')}
                </p>
              </GlassSurface>
            </div>
          </section>

          {/* Форма */}
          <section className="order-1 lg:order-2">
            <GlassSurface level="lg" className="p-6">
              <h2 className="text-title font-semibold text-fg-primary">{t('login.title')}</h2>

              {/* Вход через сервисы: GitHub */}
              <div className="mt-4 space-y-2">
                <Button
                  variant="subtle"
                  block
                  className="justify-start gap-2"
                  onClick={() => void startOAuth('github')}
                >
                  <span className="grid size-5 place-items-center rounded-pill bg-fg-primary text-caption font-semibold text-bg-base">
                    GH
                  </span>
                  {t('login.viaGithub')}
                </Button>
              </div>

              <div className="my-4 flex items-center gap-3" aria-hidden="true">
                <span className="h-px flex-1 bg-stroke-subtle" />
                <span className="text-caption uppercase tracking-wide text-fg-tertiary">{t('login.or')}</span>
                <span className="h-px flex-1 bg-stroke-subtle" />
              </div>

              <form onSubmit={submit} className="space-y-3">
                <Field label={t('login.email')}>
                  <Input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder={t('login.emailPlaceholder')}
                    autoComplete="username"
                    required
                  />
                </Field>
                <Field
                  label={t('login.password')}
                  error={error ?? undefined}
                  hint={
                    DEMO_HINT_ENABLED && !error ? (
                      <>
                        <span className="block">
                          {t('login.demoHint', {
                            email: DEMO_CREDENTIALS.email,
                            password: DEMO_CREDENTIALS.password,
                          })}
                        </span>
                        <span className="block">
                          {t('login.adminHint', {
                            email: ADMIN_CREDENTIALS.email,
                            password: ADMIN_CREDENTIALS.password,
                          })}
                        </span>
                      </>
                    ) : undefined
                  }
                >
                  <Input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    placeholder={t('login.passwordPlaceholder')}
                    autoComplete="current-password"
                    invalid={Boolean(error)}
                    onKeyDown={(event) => {
                      // Явный submit: не все браузеры отправляют форму по Enter
                      // из поля пароля (особенно после автозаполнения).
                      if (event.key === 'Enter' && !pending) {
                        event.preventDefault()
                        event.currentTarget.form?.requestSubmit()
                      }
                    }}
                    required
                  />
                </Field>
                <Button type="submit" block disabled={pending}>
                  {pending ? t('state.loading') : t('login.submit')}
                </Button>
              </form>

              <p className="mt-3 text-caption text-fg-tertiary">
                {t('login.noAccount')}{' '}
                <Link to="/register" className="font-medium text-accent hover:underline">
                  {t('login.createAccount')}
                </Link>
              </p>

              <p className="mt-4 text-caption leading-relaxed text-fg-tertiary">
                {t('login.legal')}{' '}
                <a href="#terms" className="text-accent hover:underline">
                  {t('login.terms')}
                </a>{' '}
                {t('login.or')}{' '}
                <a href="#privacy" className="text-accent hover:underline">
                  {t('login.privacy')}
                </a>
              </p>
            </GlassSurface>
          </section>
        </div>
      </div>
    </div>
  )
}
