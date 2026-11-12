/**
 * HTTP client for the backend.
 *
 * All communication goes through it so behavior is identical across requests:
 * - base `/api` (in dev vite proxies it to localhost:8000, in prod — nginx);
 * - cookie session (`credentials: 'include'`), the backend sets the token itself;
 * - errors become `ApiError` with the code and text from the server;
 * - 401 is delivered via a separate callback so the app can log the user out.
 */

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'

export class ApiError extends Error {
  readonly status: number
  /** Full response body: services return `{detail: "..."}` */
  readonly payload: unknown

  constructor(status: number, message: string, payload?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }

  /** Readable text for a toast: the server already sends a human-friendly `detail`. */
  get detail(): string {
    const payload = this.payload as { detail?: unknown } | null
    if (payload && typeof payload === 'object' && 'detail' in payload) {
      const detail = payload.detail
      if (typeof detail === 'string') return detail
      // Pydantic validation errors: [{loc, msg, type}]
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

/** 401 handler: the app replaces it with "log out and redirect to /login". */
let unauthorizedHandler: (() => void) | null = null

export function onUnauthorized(handler: (() => void) | null) {
  unauthorizedHandler = handler
}

export type QueryValue = string | number | boolean | null | undefined | Array<string | number>

/** Builds a query string, expanding arrays into repeated parameters. */
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
  /** JSON body: serialized automatically */
  body?: unknown
  /** Form body (for `/auth/login`, where OAuth2 expects form-urlencoded) */
  form?: Record<string, string>
  query?: Record<string, QueryValue>
  signal?: AbortSignal
  /** Don't log out on 401: needed by login itself and the session check */
  skipAuthRedirect?: boolean
  /** Don't try to refresh the access token: needed by /auth/refresh itself and login */
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
 * Access token refresh. One shared request for all parallel 401s:
 * otherwise ten widgets would refresh the session at once and overwrite the cookie.
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

/** 401 → one refresh → one retry of the original request. */
async function send(path: string, options: RequestOptions): Promise<Response> {
  let response = await rawRequest(path, options)
  if (response.status === 401 && !options.skipAuthRefresh) {
    if (await refreshSession()) response = await rawRequest(path, options)
  }
  return response
}

/** Error body: the server sends `{detail}` in FastAPI format. */
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

/** Request with JSON parsing and error normalization. */
export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await send(path, options)
  if (!response.ok) throw await parseError(response, options)

  if (response.status === 204) return undefined as T
  const text = await response.text()
  if (!text) return undefined as T
  return JSON.parse(text) as T
}

/** Request that needs response headers (`X-Total-Count` in the records list). */
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
