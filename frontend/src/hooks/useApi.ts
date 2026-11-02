/**
 * Небольшие хуки для запросов к API.
 *
 * Полноценный кэш здесь не нужен: экранов немного, данные меняются после
 * собственных мутаций. Поэтому — загрузка с состоянием `loading/error`,
 * отмена устаревших ответов и ручной `reload` после записи.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '@/api'

export interface QueryState<T> {
  data: T | null
  error: ApiError | null
  loading: boolean
  reload: () => void
}

/** Запрос, который перезапускается при изменении `deps`. */
export function useApiQuery<T>(factory: () => Promise<T>, deps: unknown[] = []): QueryState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  const mounted = useRef(true)

  const factoryRef = useRef(factory)
  factoryRef.current = factory

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    factoryRef
      .current()
      .then((result) => {
        if (cancelled || !mounted.current) return
        setData(result)
        setError(null)
      })
      .catch((caught: unknown) => {
        if (cancelled || !mounted.current) return
        setError(caught instanceof ApiError ? caught : new ApiError(0, String(caught)))
      })
      .finally(() => {
        if (cancelled || !mounted.current) return
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])

  const reload = useCallback(() => setTick((value) => value + 1), [])

  return { data, error, loading, reload }
}

/** Значение с задержкой: поиск по вводу не должен бить в API на каждую букву. */
export function useDebounced<T>(value: T, delay = 350): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

/** Асинхронное действие с состоянием «выполняется» — для кнопок сохранения. */
export function useMutation<TArgs extends unknown[], TResult>(
  action: (...args: TArgs) => Promise<TResult>,
): { run: (...args: TArgs) => Promise<TResult | null>; pending: boolean; error: ApiError | null } {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)

  const run = useCallback(
    async (...args: TArgs) => {
      setPending(true)
      setError(null)
      try {
        return await action(...args)
      } catch (caught) {
        setError(caught instanceof ApiError ? caught : new ApiError(0, String(caught)))
        return null
      } finally {
        setPending(false)
      }
    },
    [action],
  )

  return { run, pending, error }
}
