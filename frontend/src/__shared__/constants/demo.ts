/**
 * Test credentials for local development.
 *
 * The demo user with data is created by `backend/scripts/seed_demo.py`, the
 * superuser admin by `backend/scripts/seed_admin.py`. Hints are shown only in
 * dev builds (`import.meta.env.DEV`) so test credentials never appear on the
 * production login form.
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
