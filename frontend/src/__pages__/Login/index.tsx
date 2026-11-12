import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
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

/** Where to return the user after login: the path they were taken from to /login. */
function useRedirectTarget(): string {
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from
  return from && !from.startsWith('/login') ? from : '/'
}

/**
 * "Login screen": promo and the mobile app on the left, the form on the right.
 * At 390 px the panels stack vertically, the promo goes below as secondary.
 *
 * The form works with the real backend: `POST /api/auth/login` puts the token into
 * an httpOnly cookie, then the app navigates to the requested screen.
 */
export function LoginPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const redirectTo = useRedirectTarget()
  const { toast } = useToast()
  const signIn = useAuthStore((state) => state.signIn)
  const status = useAuthStore((state) => state.status)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * External login: send the browser to the backend, which redirects to the provider.
   * If the keys aren't configured on the server it answers 503 — show a clear toast
   * instead of a "broken" page.
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

  /* Already logged in? No login form needed: send to the requested screen
     (usually the main one). SessionGate has already checked the session by now. */
  if (status === 'authenticated') {
    return <Navigate to={redirectTo} replace />
  }

  return (
    <div className="relative min-h-dvh">
      <GlassBackdrop />

      <div className="relative z-[1] mx-auto flex min-h-dvh w-full max-w-container flex-col gap-6 px-4 py-6 md:px-6">
        <header className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
          <Link to="/" className="rounded-sm focus-visible:outline-none">
            <Wordmark />
          </Link>
          {/* At 390 px the pair of switchers is wider than the row: stack full-width */}
          <div className="flex w-full flex-col items-stretch gap-2 sm:w-auto sm:flex-row sm:items-center">
            <LanguageSwitcher />
            <ThemeSwitcher stretch />
          </div>
        </header>

        <div className="grid flex-1 items-center gap-8 pb-6 lg:grid-cols-[1.15fr_minmax(380px,460px)]">
          {/* Promo */}
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

          {/* Form */}
          <section className="order-1 lg:order-2">
            <GlassSurface level="lg" className="p-6">
              <h2 className="text-title font-semibold text-fg-primary">{t('login.title')}</h2>

              {/* Login via services: GitHub */}
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
                      // Explicit submit: not all browsers submit the form on Enter
                      // from the password field (especially after autofill).
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
