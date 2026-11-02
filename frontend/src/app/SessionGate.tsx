import { useEffect, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { onUnauthorized } from '@/api'
import { useAuthStore } from '@/store/auth'
import { useFinanceStore } from '@/store/finance'
import { useI18n } from '@/i18n'

/**
 * Проверка сессии при старте.
 *
 * Токен в httpOnly-cookie, поэтому «вошёл или нет» узнаём запросом профиля.
 * Пока идёт проверка, экран не мигает формой входа — показываем заглушку.
 */
function SessionGate({ children }: { children: ReactNode }) {
  const status = useAuthStore((state) => state.status)
  const bootstrap = useAuthStore((state) => state.bootstrap)
  const loadAll = useFinanceStore((state) => state.loadAll)
  const ready = useFinanceStore((state) => state.ready)
  const clear = useAuthStore((state) => state.clear)
  const { t } = useI18n()

  useEffect(() => {
    void bootstrap()
  }, [bootstrap])

  // Любой 401 от API — сессия истекла: сбрасываем состояние и уводим на вход
  useEffect(() => {
    onUnauthorized(() => clear())
    return () => onUnauthorized(null)
  }, [clear])

  // Справочники грузим один раз после входа: их читают почти все экраны
  useEffect(() => {
    if (status === 'authenticated') void loadAll()
  }, [status, loadAll])

  /* Ждём и сессию, и справочники: иначе первый кадр показывает пустые экраны */
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

/** Роут только для вошедших: иначе — на страницу входа с запоминанием адреса. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const status = useAuthStore((state) => state.status)
  const location = useLocation()

  if (status !== 'authenticated') {
    return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  }
  return <>{children}</>
}

export { SessionGate }
