import { useEffect, type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { onUnauthorized } from '@/api'
import { useAuthStore } from '@/store/auth'
import { useFinanceStore } from '@/store/finance'
import { useRecordsStore } from '@/store/records'
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
  const clearData = useFinanceStore((state) => state.clearData)
  const ready = useFinanceStore((state) => state.ready)
  const clear = useAuthStore((state) => state.clear)
  /** Кто вошёл: смена пользователя должна стирать данные предыдущего */
  const userId = useAuthStore((state) => state.user?.id ?? null)
  const { t } = useI18n()

  useEffect(() => {
    void bootstrap()
  }, [bootstrap])

  // Любой 401 от API — сессия истекла: сбрасываем состояние и уводим на вход
  useEffect(() => {
    onUnauthorized(() => clear())
    return () => onUnauthorized(null)
  }, [clear])

  /* Справочники читают почти все экраны, поэтому грузим их при входе.
     Ключ — id пользователя: при выходе данные стираем, при смене аккаунта
     стираем и загружаем заново, иначе новый пользователь увидел бы чужое. */
  useEffect(() => {
    clearData()
    useRecordsStore.getState().reset()
    if (userId) void loadAll()
  }, [userId, clearData, loadAll])

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

/** Роут только для суперпользователей: остальным — на главную. */
export function RequireSuperuser({ children }: { children: ReactNode }) {
  const user = useAuthStore((state) => state.user)

  if (!user?.is_superuser) {
    return <Navigate to="/" replace />
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
