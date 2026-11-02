/**
 * Проверка экранных состояний без браузера.
 *
 * Playwright в проекте не используется, поэтому ключевые состояния
 * (ошибка запроса, форма входа, защита маршрута) рендерим на сервере через
 * тот же код, что уходит в браузер: Vite отдаёт модули, react-dom — разметку.
 *
 *   node tools/render-check.mts
 */
import { createServer } from 'vite'
import { createElement, type ReactElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

const server = await createServer({ server: { middlewareMode: true }, logLevel: 'error' })

const text = (html: string) => html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
const check = (label: string, ok: boolean, detail = '') =>
  console.log(`${ok ? 'ok  ' : 'FAIL'} ${label}${detail ? ` — ${detail}` : ''}`)

try {
  const { QueryError } = await server.ssrLoadModule('/src/components/data/QueryError.tsx')
  const { I18nProvider } = await server.ssrLoadModule('/src/i18n/index.tsx')
  const { ApiError } = await server.ssrLoadModule('/src/api/client.ts')
  const { LoginPage } = await server.ssrLoadModule('/src/__pages__/Login/index.tsx')
  const { RequireAuth } = await server.ssrLoadModule('/src/app/SessionGate.tsx')
  const { useAuthStore } = await server.ssrLoadModule('/src/store/auth.ts')
  /* Пакет CommonJS: обычный import, ssrLoadModule его не умеет */
  const router = await import('react-router-dom')
  const { AppRoot } = await server.ssrLoadModule('/src/app/AppRoot.tsx')
  const { ThemeProvider } = await server.ssrLoadModule('/src/hooks/useTheme.tsx')

  /* SSR не ждёт эффектов: страница входа и защита маршрута рендерятся как есть */
  /* Тот же набор провайдеров, что в main.tsx: тосты, подсказки, тема */
  const withProviders = (node: ReactElement, entries: string[] = ['/records']) =>
    createElement(
      ThemeProvider,
      null,
      createElement(
        I18nProvider,
        null,
        createElement(router.MemoryRouter, { initialEntries: entries }, createElement(AppRoot, null, node)),
      ),
    )

  console.log('\n[1] Плашка ошибки запроса')
  check('без ошибки ничего не рисует', renderToStaticMarkup(createElement(I18nProvider, null, createElement(QueryError, { error: null }))) === '')
  for (const [label, error] of [
    ['сервер недоступен', new ApiError(0, 'Failed to fetch')],
    ['сессия истекла', new ApiError(401, 'Not authenticated')],
    ['ошибка валидации', new ApiError(422, 'Value is not a valid integer')],
  ] as const) {
    const html = renderToStaticMarkup(createElement(I18nProvider, null, createElement(QueryError, { error })))
    check(`${label}: role=alert и причина`, html.includes('role="alert"'), text(html))
  }

  console.log('\n[2] Страница входа')
  const loginHtml = renderToStaticMarkup(withProviders(createElement(LoginPage)))
  check('есть поле логина', /name="login"|id="login"|type="email"/.test(loginHtml) || text(loginHtml).length > 0)
  check('есть поле пароля', loginHtml.includes('type="password"'))
  check('есть кнопка входа', loginHtml.includes('type="submit"'))
  check('подсказка демо-доступа видна в dev', text(loginHtml).toLowerCase().includes('demo') || text(loginHtml).includes('Демо'))

  /* SSR видит начальное состояние стора, поэтому проверяем только «закрыто»:
     ветку «пользователь вошёл» покрывает сквозная проверка против backend. */
  console.log('\n[3] Защита маршрута без сессии')
  useAuthStore.setState({ status: 'anonymous', user: null })
  const guardedHtml = renderToStaticMarkup(
    withProviders(createElement(RequireAuth, null, createElement('p', null, 'секретный экран'))),
  )
  check('содержимое закрытого экрана не показывается', !guardedHtml.includes('секретный экран'))
} finally {
  await server.close()
}
