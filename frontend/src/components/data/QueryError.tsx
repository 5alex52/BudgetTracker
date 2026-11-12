import { AlertCircle } from 'lucide-react'
import type { ApiError } from '@/api'
import { useI18n } from '@/i18n'

/**
 * Failed-request message.
 *
 * Without it a server failure looks like "no data": charts draw zeros
 * and the user doesn't realize the numbers aren't real.
 */
export function QueryError({ error, className }: { error: ApiError | null; className?: string }) {
  const { t } = useI18n()
  if (!error) return null

  const description =
    error.status === 0 ? t('api.network') : error.status === 401 ? t('api.unauthorized') : error.detail

  return (
    <div
      role="alert"
      className={`flex items-start gap-2 rounded-lg border border-[var(--negative)]/40 bg-[var(--negative)]/5 px-3 py-2 ${className ?? ''}`}
    >
      <AlertCircle className="mt-0.5 size-4 shrink-0 text-[var(--negative)]" aria-hidden="true" />
      <div className="min-w-0">
        <p className="text-label text-fg-primary">{t('api.requestFailed')}</p>
        <p className="truncate text-caption text-fg-tertiary">{description}</p>
      </div>
    </div>
  )
}
