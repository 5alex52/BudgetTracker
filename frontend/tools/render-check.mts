/**
 * Screen-state checks without a browser.
 *
 * Playwright is not used in this project, so key states (request error, login
 * form, route guard) are rendered on the server through the same code that
 * ships to the browser: Vite serves the modules, react-dom produces the markup.
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
  /* CommonJS package: plain import, ssrLoadModule cannot handle it */
  const router = await import('react-router-dom')
  const { AppRoot } = await server.ssrLoadModule('/src/app/AppRoot.tsx')
  const { ThemeProvider } = await server.ssrLoadModule('/src/hooks/useTheme.tsx')

  /* SSR does not wait for effects: the login page and route guard render as-is */
  /* Same provider set as main.tsx: toasts, tooltips, theme */
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

  console.log('\n[1] Request error banner')
  check('renders nothing without an error', renderToStaticMarkup(createElement(I18nProvider, null, createElement(QueryError, { error: null }))) === '')
  for (const [label, error] of [
    ['server unavailable', new ApiError(0, 'Failed to fetch')],
    ['session expired', new ApiError(401, 'Not authenticated')],
    ['validation error', new ApiError(422, 'Value is not a valid integer')],
  ] as const) {
    const html = renderToStaticMarkup(createElement(I18nProvider, null, createElement(QueryError, { error })))
    check(`${label}: role=alert and a reason`, html.includes('role="alert"'), text(html))
  }

  console.log('\n[2] Login page')
  const loginHtml = renderToStaticMarkup(withProviders(createElement(LoginPage)))
  check('has a login field', /name="login"|id="login"|type="email"/.test(loginHtml) || text(loginHtml).length > 0)
  check('has a password field', loginHtml.includes('type="password"'))
  check('has a submit button', loginHtml.includes('type="submit"'))
  check('demo-access hint visible in dev', text(loginHtml).toLowerCase().includes('demo') || text(loginHtml).includes('Демо'))
  check('admin-access hint visible in dev', text(loginHtml).toLowerCase().includes('admin') || text(loginHtml).includes('Админ'))

  /* SSR sees the store's initial state, so we only check the "closed" branch:
     the "user is signed in" branch is covered by the end-to-end check against the backend. */
  console.log('\n[3] Route guard without a session')
  useAuthStore.setState({ status: 'anonymous', user: null })
  const guardedHtml = renderToStaticMarkup(
    withProviders(createElement(RequireAuth, null, createElement('p', null, 'secret screen'))),
  )
  check('guarded screen content is not shown', !guardedHtml.includes('secret screen'))
} finally {
  await server.close()
}
