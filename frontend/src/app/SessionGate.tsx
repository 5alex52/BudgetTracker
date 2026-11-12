import { useEffect, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { onUnauthorized } from '@/api'
import { useAuthStore } from '@/store/auth'
import { useFinanceStore } from '@/store/finance'
import { useRecordsStore } from '@/store/records'
import { useI18n } from '@/i18n'

/**
 * Session check at startup.
 *
 * The token is in an httpOnly cookie, so "logged in or not" is determined by a profile request.
 * While the check runs, the screen doesn't flash the login form — we show a placeholder.
 */
function SessionGate({ children }: { children: ReactNode }) {
  const status = useAuthStore((state) => state.status)
  const bootstrap = useAuthStore((state) => state.bootstrap)
  const loadAll = useFinanceStore((state) => state.loadAll)
  const clearData = useFinanceStore((state) => state.clearData)
  const ready = useFinanceStore((state) => state.ready)
  const clear = useAuthStore((state) => state.clear)
  /** Who is logged in: a user switch must wipe the previous user's data */
  const userId = useAuthStore((state) => state.user?.id ?? null)
  const { t } = useI18n()

  useEffect(() => {
    void bootstrap()
  }, [bootstrap])

  // Any 401 from the API means the session expired: reset state and go to login
  useEffect(() => {
    onUnauthorized(() => clear())
    return () => onUnauthorized(null)
  }, [clear])

  /* Almost every screen reads reference data, so we load it on login.
     Keyed by user id: on logout the data is wiped, on account switch
     it's wiped and reloaded, otherwise the new user would see someone else's. */
  useEffect(() => {
    clearData()
    useRecordsStore.getState().reset()
    if (userId) void loadAll()
  }, [userId, clearData, loadAll])

  /* Wait for both the session and reference data: otherwise the first frame shows empty screens */
  if (status === 'loading' || (status === 'authenticated' && !ready)) {
    return (
      <div className="grid min-h-dvh place-items-center">
        <p role="status" className="text-label text-fg-tertiary">
          {t('common.loading')}
        </p>
      </div>
    )
  }

  return <>{children}</>
}

/** Superusers-only route: everyone else goes to the main page. */
export function RequireSuperuser({ children }: { children: ReactNode }) {
  const user = useAuthStore((state) => state.user)

  if (!user?.is_superuser) {
    return <Navigate to="/" replace />
  }
  return <>{children}</>
}

/** Logged-in-only route: otherwise — to the login page, remembering the address. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const status = useAuthStore((state) => state.status)
  const location = useLocation()

  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }
  return <>{children}</>
}

export { SessionGate }
