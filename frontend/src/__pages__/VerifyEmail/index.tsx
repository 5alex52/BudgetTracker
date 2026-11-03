import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CheckCircle2, XCircle } from 'lucide-react'
import { useI18n } from '@/i18n'
import { authApi } from '@/api'
import { ApiError } from '@/api/client'
import { useAuthStore } from '@/store/auth'
import { Wordmark } from '@/components/brand/Logo'
import { GlassBackdrop } from '@/components/glass/GlassBackdrop'
import { GlassSurface } from '@/components/glass/GlassSurface'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/toast'

/**
 * Страница по ссылке из письма: `/verify-email?token=…`.
 *
 * Токен одноразовый, поэтому подтверждение запускается сразу при открытии —
 * повторный клик по ссылке из письма просто покажет «уже подтверждён».
 * После успешного подтверждения происходит автоматический вход.
 */
export function VerifyEmailPage() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const { toast } = useToast()
  const bootstrap = useAuthStore((state) => state.bootstrap)
  const [state, setState] = useState<'checking' | 'ok' | 'failed'>('checking')
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    const token = new URLSearchParams(window.location.search).get('token')
    if (!token) {
      setState('failed')
      setMessage(t('verify.missingToken'))
      return
    }

    let cancelled = false
    authApi
      .verifyEmail(token)
      .then(() => {
        if (cancelled) return
        setState('ok')
        // Автоматический вход после подтверждения: перечитываем профиль
        return bootstrap()
      })
      .then(() => {
        if (cancelled) return
        toast({ title: t('verify.success'), description: t('verify.successHint'), tone: 'success' })
        // Перенаправляем на главную через небольшую задержку, чтобы toast успел показаться
        setTimeout(() => navigate('/', { replace: true }), 500)
      })
      .catch((caught: unknown) => {
        if (cancelled) return
        setState('failed')
        setMessage(caught instanceof ApiError ? caught.detail : String(caught))
      })
    return () => {
      cancelled = true
    }
  }, [t, navigate, toast, bootstrap])

  return (
    <div className="relative min-h-dvh">
      <GlassBackdrop />
      <div className="relative z-[1] mx-auto flex min-h-dvh w-full max-w-container flex-col gap-6 px-4 py-6 md:px-6">
        <header>
          <Link to="/" className="rounded-sm focus-visible:outline-none">
            <Wordmark />
          </Link>
        </header>

        <div className="grid flex-1 place-items-center">
          <GlassSurface level="lg" className="w-full max-w-md p-6 text-center">
            {state === 'checking' && (
              <p className="text-label text-fg-secondary" role="status">
                {t('verify.checking')}
              </p>
            )}

            {state === 'ok' && (
              <>
                <CheckCircle2 className="mx-auto size-10 text-[var(--positive)]" aria-hidden="true" />
                <h1 className="mt-3 text-title font-semibold text-fg-primary">{t('verify.success')}</h1>
                <p className="mt-2 text-caption text-fg-secondary">{t('verify.successHint')}</p>
              </>
            )}

            {state === 'failed' && (
              <>
                <XCircle className="mx-auto size-10 text-[var(--negative)]" aria-hidden="true" />
                <h1 className="mt-3 text-title font-semibold text-fg-primary">{t('verify.failed')}</h1>
                <p className="mt-2 text-caption text-fg-secondary">{message ?? t('verify.failedHint')}</p>
                <Link to="/login" className="mt-4 inline-block">
                  <Button variant="subtle">{t('login.submit')}</Button>
                </Link>
              </>
            )}
          </GlassSurface>
        </div>
      </div>
    </div>
  )
}
