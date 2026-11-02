/**
 * Тестовые доступы для локальной разработки.
 *
 * Пользователя с данными создаёт `backend/scripts/seed_demo.py`, администратора
 * с правами суперпользователя — `backend/scripts/seed_admin.py`. Подсказки
 * показываются только в dev-сборке (`import.meta.env.DEV`), чтобы в продакшене
 * на форме входа не висели тестовые учётные данные.
 */
const DOMAIN = 'budgettracker.local'

export const DEMO_CREDENTIALS = {
  email: `${'demo'}@${DOMAIN}`,
  password: 'demo12345',
}

export const ADMIN_CREDENTIALS = {
  email: `${'admin'}@${DOMAIN}`,
  password: 'admin12345',
}

export const DEMO_HINT_ENABLED = import.meta.env.DEV
