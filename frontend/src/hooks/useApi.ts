/**
 * Small hooks for API requests.
 *
 * A full cache isn't needed here: there are few screens and data changes after
 * our own mutations. So — loading with `loading/error` state, cancelling stale
 * responses and a manual `reload` after a write.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '@/api'
import { useFinanceStore } from '@/store/finance'

export interface QueryState<T> {
  data: T | null
  error: ApiError | null
  loading: boolean
  reload: () => void
}

/** A request that re-runs when `deps` change. */
export function useApiQuery<T>(factory: () => Promise<T>, deps: unknown[] = []): QueryState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  // Any record/account edit bumps the revision — widgets re-fetch data
  const revision = useFinanceStore((state) => state.revision)
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
  }, [...deps, tick, revision])

  const reload = useCallback(() => setTick((value) => value + 1), [])

  return { data, error, loading, reload }
}

/** Debounced value: search-as-you-type must not hit the API on every keystroke. */
export function useDebounced<T>(value: T, delay = 350): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}
