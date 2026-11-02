/**
 * Демо-доступ для локальной разработки.
 *
 * Пользователь создаётся скриптом `backend/scripts/seed_demo.py`. Подсказка
 * показывается только в dev-сборке (`import.meta.env.DEV`), чтобы в продакшене
 * на форме входа не висели тестовые учётные данные.
 */
const LOGIN = 'demo'
const DOMAIN = 'budgettracker.local'

export const DEMO_CREDENTIALS = {
  email: `${LOGIN}@${DOMAIN}`,
  password: 'demo12345',
}

export const DEMO_HINT_ENABLED = import.meta.env.DEV
