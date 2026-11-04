/**
 * HTTP-клиент к backend.
 *
 * Всё общение идёт через него, чтобы поведение было одинаковым во всех запросах:
 * - база `/api` (в dev её проксирует vite на localhost:8000, в prod — nginx);
 * - cookie-сессия (`credentials: 'include'`), токен кладёт сам backend;
 * - ошибки превращаются в `ApiError` с кодом и текстом от сервера;
 * - 401 отдаётся отдельным колбэком, чтобы приложение могло разлогинить пользователя.
 */

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'

export class ApiError extends Error {
  readonly status: number
  /** Тело ответа целиком: сервисы возвращают `{detail: "..."}` */
  readonly payload: unknown

  constructor(status: number, message: string, payload?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }

  /** Понятный текст для тоста: сервер уже присылает человекочитаемый `detail`. */
  get detail(): string {
    const payload = this.payload as { detail?: unknown } | null
    if (payload && typeof payload === 'object' && 'detail' in payload) {
      const detail = payload.detail
      if (typeof detail === 'string') return detail
      // Ошибки валидации pydantic: [{loc, msg, type}]
      if (Array.isArray(detail)) {
        return detail
          .map((item) => {
            if (item && typeof item === 'object' && 'msg' in item) {
              const field = Array.isArray((item as { loc?: unknown[] }).loc)
                ? (item as { loc: unknown[] }).loc.slice(1).join('.')
                : ''
              return field ? `${field}: ${String((item as { msg: unknown }).msg)}` : String((item as { msg: unknown }).msg)
            }
            return String(item)
          })
          .join('; ')
      }
    }
    return this.message
  }
}

/** Обработчик 401: приложение подменяет его на «разлогинить и увести на /login». */
let unauthorizedHandler: (() => void) | null = null

export function onUnauthorized(handler: (() => void) | null) {
  unauthorizedHandler = handler
}

export type QueryValue = string | number | boolean | null | undefined | Array<string | number>

/** Собирает query-строку, разворачивая массивы в повторяющиеся параметры. */
export function buildQuery(params?: Record<string, QueryValue>): string {
  if (!params) return ''
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === '') continue
    if (Array.isArray(value)) {
      if (value.length === 0) continue
      value.forEach((item) => search.append(key, String(item)))
      continue
    }
    search.append(key, String(value))
  }
  const query = search.toString()
  return query ? `?${query}` : ''
}

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'
  /** JSON-тело: сериализуется автоматически */
  body?: unknown
  /** Тело формы (для `/auth/login`, где OAuth2 ждёт form-urlencoded) */
  form?: Record<string, string>
  query?: Record<string, QueryValue>
  signal?: AbortSignal
  /** Не разлогинивать при 401: нужно самому входу и проверке сессии */
  skipAuthRedirect?: boolean
  /** Не пытаться обновить access-токен: нужно самому /auth/refresh и входу */
  skipAuthRefresh?: boolean
}

export interface ApiResponse<T> {
  data: T
  headers: Headers
  status: number
}

async function rawRequest(path: string, options: RequestOptions = {}): Promise<Response> {
  const { method = 'GET', body, form, query, signal } = options
  const headers: Record<string, string> = { Accept: 'application/json' }
  let payload: BodyInit | undefined

  if (form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    payload = new URLSearchParams(form).toString()
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  const response = await fetch(`${API_BASE}${path}${buildQuery(query)}`, {
    method,
    headers,
    body: payload,
    credentials: 'include',
    signal,
  })

  return response
}

/**
 * Обновление access-токена. Один общий запрос на все параллельные 401:
 * иначе десять виджетов одновременно обновят сессию и перезапишут cookie.
 */
let refreshInFlight: Promise<boolean> | null = null

function refreshSession(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { Accept: 'application/json' },
    })
      .then((response) => response.ok)
      .catch(() => false)
      .finally(() => {
        refreshInFlight = null
      })
  }
  return refreshInFlight
}

/** 401 → один refresh → один повтор исходного запроса. */
async function send(path: string, options: RequestOptions): Promise<Response> {
  let response = await rawRequest(path, options)
  if (response.status === 401 && !options.skipAuthRefresh) {
    if (await refreshSession()) response = await rawRequest(path, options)
  }
  return response
}

/** Тело ошибки: сервер присылает `{detail}` в формате FastAPI. */
async function parseError(response: Response, options: RequestOptions): Promise<ApiError> {
  let parsed: unknown = null
  const text = await response.text()
  if (text) {
    try {
      parsed = JSON.parse(text)
    } catch {
      parsed = { detail: text }
    }
  }
  if (response.status === 401 && !options.skipAuthRedirect) {
    unauthorizedHandler?.()
  }
  const detail =
    parsed && typeof parsed === 'object' && 'detail' in parsed
      ? String((parsed as { detail: unknown }).detail)
      : `HTTP ${response.status}`
  return new ApiError(response.status, detail, parsed)
}

/** Запрос с разбором JSON и нормализацией ошибок. */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await send(path, options)
  if (!response.ok) throw await parseError(response, options)

  if (response.status === 204) return undefined as T
  const text = await response.text()
  if (!text) return undefined as T
  return JSON.parse(text) as T
}

/** Запрос, которому нужны заголовки ответа (`X-Total-Count` в списке записей). */
export async function requestWithHeaders<T>(
  path: string,
  options: RequestOptions = {},
): Promise<ApiResponse<T>> {
  const response = await send(path, options)
  if (!response.ok) throw await parseError(response, options)

  const text = await response.text()
  return {
    data: text ? (JSON.parse(text) as T) : (undefined as T),
    headers: response.headers,
    status: response.status,
  }
}

export { API_BASE }
