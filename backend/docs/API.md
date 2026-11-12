# API contract for the "Finance Tracker" frontend

This document is based on what the frontend actually renders (`frontend/src/__pages__`),
not on a wish list. For each screen it lists what data it shows, which endpoint covers it,
and whether that endpoint already exists in the service.

Legend: ✅ — already existed in the service, ➕ — added in this iteration.

Base prefixes: `/api/finance` — finance, `/api/users` — profile, `/api/analytics` —
analytics (a separate app).
Authentication: the `access_token` cookie (as in the existing `CurrentUser`), errors — standard
`401/403/404/422`.

---

## 1. Screens and their data

### 1.1 "Login" (`/login`)

| Need | Endpoint | Status |
|---|---|---|
| Log in with email and password | `POST /api/auth/login` | ✅ |
| Registration | `POST /api/auth/register` | ✅ |
| Email confirmation | `POST /api/auth/send-verification-email`, `POST /api/auth/verify-email` | ✅ |
| Log out | `POST /api/auth/logout` | ✅ |
| Who am I (header, user menu) | `GET /api/users/me` | ➕ |

### 1.2 "Overview" (`/`)

| Need | Endpoint | Status |
|---|---|---|
| Account cards with balances | `GET /api/finance/accounts` | ✅ |
| Total balance in the base currency | `GET /api/finance/accounts/balance` | ✅ (handling of excluded accounts — fixed) |
| Income/expense/net for the period + comparison with the previous one | `GET /api/analytics/summary` | ➕ |
| Daily cashflow chart | `GET /api/analytics/timeseries?metric=cashflow` | ➕ |
| Balance chart | `GET /api/analytics/timeseries?metric=balance` | ➕ |
| Expense breakdown donut chart | `GET /api/analytics/by-category` | ➕ |
| Period comparison | `GET /api/analytics/summary?compare=true` | ➕ |

### 1.3 "Accounts" (`/accounts`) and the account card (`/accounts/:id`)

| Need | Endpoint | Status |
|---|---|---|
| List, including archived | `GET /api/finance/accounts?include_archived=` | ✅ |
| Create / update / delete | `POST`, `PATCH`, `DELETE /api/finance/accounts/{id}` | ✅ |
| Archive / restore | `POST /api/finance/accounts/{id}/archive` | ✅ |
| "Excluded from statistics" | `POST /api/finance/accounts/{id}/exclude` | ➕ |
| Account summary: income, expenses, transactions | `GET /api/finance/accounts/{id}/summary` | ➕ |
| Account transactions | `GET /api/finance/transactions?account_ids=` | ✅/➕ (multi-select) |
| Export account transactions | `GET /api/finance/transactions/export?format=&account_ids=` | ➕ |

The "lock" on account cards (Alfa RUB, Tinkoff) indicates bank synchronization. The service
has no synchronization, so there is no lock: the frontend does not render it.

### 1.4 "Records" (`/records`)

| Need | Endpoint | Status |
|---|---|---|
| List with filters and pagination | `GET /api/finance/transactions` | ✅/➕ (extended) |
| Filters: accounts, categories, currencies, types — multi-select | `account_ids`, `category_ids`, `currency_ids`, `types` | ➕ |
| Search by note, category, account | `q` | ➕ |
| Amount range | `amount_min`, `amount_max` | ➕ |
| Sorting (date, amount) | `sort` | ➕ |
| Total record count for "show more" | `X-Total-Count` header | ➕ |
| Create / update / delete | `POST`, `PATCH`, `DELETE` | ✅ |
| Bulk delete selected | `POST /api/finance/transactions/bulk-delete` | ➕ |
| Export CSV / JSON for a period | `GET /api/finance/transactions/export` | ➕ |
| Import records from an export file | `POST /api/finance/transactions/import` | ➕ |
| Category summary for the period | `GET /api/finance/transactions/summary` | ✅ |

A record card returns `TransactionWithDetails` — with the category name and color, the account name and
the currency symbol: without these the edit dialog cannot be filled.

### 1.5 "Analytics" (`/analytics`)

| Need | Endpoint | Status |
|---|---|---|
| Period totals and comparison | `GET /api/analytics/summary` | ➕ |
| "Categories × months" report | `GET /api/analytics/matrix` | ➕ |
| Breakdown by categories and subcategories | `GET /api/analytics/by-category` | ➕ |
| Breakdown by accounts | `GET /api/analytics/by-account` | ➕ |
| Dynamics by day/week/month | `GET /api/analytics/timeseries` | ➕ |

Analytics lives in a separate app (`src/analytics/`) under its own prefix
`/api/analytics`: it is a read model over the financial data, with no CRUD and no DB writes of its own.

### 1.6 "Settings" (`/settings` and its sections)

| Screen | Need | Endpoint | Status |
|---|---|---|---|
| Profile | Read and edit name, email, language, timezone, base currency | `GET`, `PATCH /api/users/me` | ➕ |
| Profile | Change password | `POST /api/users/me/password` | ➕ |
| Profile | Avatar | `PATCH /api/users/me` (`photo` field) | ➕ |
| Currencies | Currency list with rates | `GET /api/finance/currencies` | ✅ |
| Currencies | Rates relative to the selected base | `GET /api/finance/currencies/rates?base=BYN` | ➕ |
| Currencies | Edit a rate in the catalog | `PATCH /api/finance/currencies/{code}` | ✅ (superuser only) |
| Currencies | Personal rate for your own calculations | `PUT`, `DELETE /api/finance/currencies/{code}/rate` | ➕ |
| Categories | Tree: category → subcategories with counters | `GET /api/finance/categories/tree` | ➕ |
| Categories | How many records and for what amount | `GET /api/finance/categories/stats` | ➕ |
| Categories | CRUD, subcategories via `parent_id` | `GET/POST/PATCH/DELETE /api/finance/categories` | ✅ |
| Privacy | Download your data | `GET /api/users/me/export` | ➕ |
| Privacy | Delete account | `DELETE /api/users/me` | ➕ |
| Tags | Tag list with counters, CRUD | `GET/POST/PATCH/DELETE /api/finance/tags` | ➕ |
| Templates | List and CRUD of quick-entry templates | `GET/POST/PATCH/DELETE /api/finance/templates` | ➕ |
| Templates | Create a record from a template | `POST /api/finance/templates/{id}/apply` | ➕ |
| Rules | List and CRUD of auto-categorization rules | `GET/POST/PATCH/DELETE /api/finance/rules` | ➕ |
| Rules | Apply rules to existing records | `POST /api/finance/rules/apply` | ➕ |

### 1.7 What the frontend does itself

- CSV/TSV/XLS/JSON/PDF export — currently client-side from already loaded data; PDF via browser
  printing. Server-side export (`/transactions/export`) is only needed for dumping a period
  that doesn't fit on the page; we don't do PDF on the server (no generator in the dependencies).
- UI theme and language — stored in `localStorage`; only the user's preference (`locale`)
  is kept on the server so new devices start with it.
- All charts are built on the client from aggregates; the server only returns numbers.

---

## 2. Added endpoints: full list

### Profile

```
GET    /api/users/me                    → User
PATCH  /api/users/me                    → User           (firstname, lastname, email, photo, timezone,
                                                          locale, theme, base_currency)
POST   /api/users/me/password           → 204            (old_password, new_password)
GET    /api/users/me/export             → JSON archive   (accounts, categories, records, rates)
DELETE /api/users/me                    → 204            (body: {"password": "..."} — cascade delete)
```

### Accounts

```
POST   /api/finance/accounts/{id}/exclude?is_excluded=true → AccountResponse
GET    /api/finance/accounts/{id}/summary?start_date&end_date → AccountSummary
GET    /api/finance/accounts/balance                       → BalanceOverview (without excluded accounts)
```

### Categories

```
GET    /api/finance/categories/tree?category_type=expense&start_date&end_date → List[CategoryNode]
GET    /api/finance/categories/stats?category_type&start_date&end_date        → List[CategoryStat]
```

### Records

```
GET    /api/finance/transactions?account_ids=1&account_ids=2&category_ids=&currency_ids=&types=&
                             q=&amount_min=&amount_max=&start_date=&end_date=&sort=&
                             with_total=true&offset=&limit=
                                                          → List[TransactionWithDetails] + X-Total-Count
                                                          sort: date_desc | date_asc | amount_desc | amount_asc
POST   /api/finance/transactions/bulk-delete              → {deleted: int, missing: [int]}
                                                          body: {"ids": [1, 2, 3]}
GET    /api/finance/transactions/export?format=csv|json&… → file (up to 5000 records)
POST   /api/finance/transactions/import                   → {created, accounts_created,
                                                          categories_created, skipped, errors[]}
                                                          body: {"format": "csv|json", "content": "<file>"}
                                                          missing account/category — created
                                                          transfers are skipped (the export has no destination account)
```

### Analytics (separate app, prefix `/api/analytics`)

```
GET /api/analytics/summary?start_date&end_date&compare=true      → AnalyticsSummary
GET /api/analytics/timeseries?start_date&end_date&group_by=day|week|month&metric=cashflow|balance
GET /api/analytics/by-category?start_date&end_date&transaction_type=expense&parent_id&
                               include_children=true&rollup=false
GET /api/analytics/by-account?start_date&end_date
GET /api/analytics/matrix?months=6&transaction_type=expense&rollup=true&end_date
```

### Currencies and personal rates

```
GET /api/finance/currencies/rates?base=BYN                → List[CurrencyRate]
PUT /api/finance/currencies/{code}/rate                   → CurrencyRate   (body: {"rate": 2.5})
DELETE /api/finance/currencies/{code}/rate                → 204
```

`base` defaults to BYN — the service's base currency. An unknown code → `400` (silently
substituting another currency is not allowed: the rate would then be computed incorrectly).

`/rates` is public: the catalog is not personal data. If the user is authenticated,
the response takes their personal rates into account — those have `is_custom: true`. `PUT`/`DELETE` require login:
the catalog is shared, while a personal rate belongs to the user.

### Tags

```
GET    /api/finance/tags/                → List[TagResponse] (+transactions_count)
POST   /api/finance/tags/                → TagResponse   (name, color)
GET    /api/finance/tags/{tag_id}        → TagResponse
PATCH  /api/finance/tags/{tag_id}        → TagResponse
DELETE /api/finance/tags/{tag_id}        → 204          (links to records are removed, the records remain)

GET /api/finance/transactions?tag_ids=1&tag_ids=2        → records with at least one of the tags
POST /api/finance/transactions/  {"tag_ids": [1, 2]}     → tags are attached on creation
PATCH /api/finance/transactions/{id} {"tag_ids": []}     → an empty list removes all tags
```

### Quick-entry templates

```
GET    /api/finance/templates/                 → List[TemplateResponse] (most used first)
POST   /api/finance/templates/                 → TemplateResponse
GET    /api/finance/templates/{template_id}    → TemplateResponse
PATCH  /api/finance/templates/{template_id}    → TemplateResponse
DELETE /api/finance/templates/{template_id}    → 204
POST   /api/finance/templates/{template_id}/apply?date=…   → TransactionResponse
```

`apply` creates a record through the same service as regular creation: rules fire,
the account balance is recomputed, and the template's `usage_count` is incremented by one.

### Auto-categorization rules

```
GET    /api/finance/rules/              → List[RuleResponse] (ascending priority)
POST   /api/finance/rules/              → RuleResponse
GET    /api/finance/rules/{rule_id}     → RuleResponse
PATCH  /api/finance/rules/{rule_id}     → RuleResponse
DELETE /api/finance/rules/{rule_id}     → 204
POST   /api/finance/rules/apply?start_date&end_date&dry_run=false → RuleApplyResult
```

Condition: `field` = `note` | `amount`, `operator` = `contains` | `equals` | `greater` | `less`.
Actions (several at once allowed): `set_category_id`, `add_tag_id`, `exclude_from_statistics`.

Rules are applied when a record is created and when `apply` is called. Records hidden from statistics
remain in lists — they have `is_excluded: true`, and aggregates ignore them.

---

## 3. Response formats

All amounts are in the user's base currency, rounded to 2 decimal places. The rate is taken from
personal currency settings (`user_currency_rates`), or from the `currencies` catalog if none are set.
Periods are ISO-8601; `start_date`/`end_date` are validated through the existing
`normalize_period`.

```jsonc
// GET /api/analytics/summary?start_date=2025-10-01&end_date=2025-10-31&compare=true
{
  "start_date": "2025-10-01T00:00:00",
  "end_date": "2025-10-31T23:59:59",
  "income": 12267.07,
  "expense": 3329.15,
  "net": 8937.92,
  "transactions_count": 148,
  "previous": {                      // null if compare=false
    "start_date": "...", "end_date": "...",
    "income": 8297.03, "expense": 3510.44, "net": 4786.59, "transactions_count": 121
  },
  "change": {                        // percentages relative to the previous period
    "income": 47.85, "expense": -5.17, "net": 86.72
  }
}
```

```jsonc
// GET /api/analytics/timeseries?metric=cashflow&group_by=day
{ "group_by": "day", "metric": "cashflow", "points": [
    { "date": "2025-10-01T00:00:00", "income": 1200.0, "expense": 400.0, "net": 800.0 } ] }

// metric=balance — cumulative balance across all accounts at the end of the interval
{ "group_by": "day", "metric": "balance", "points": [
    { "date": "2025-10-01T00:00:00", "value": 12600.0 } ] }
```

```jsonc
// GET /api/analytics/by-category?type=expense
{ "items": [ { "category_id": 7, "name": "Еда и напитки", "color": "#e0913c", "icon": "utensils",
               "parent_id": null, "total": 609.4, "share": 18.3, "transactions_count": 42 } ],
  "total": 3329.15 }

// GET /api/analytics/by-account
{ "items": [ { "account_id": 3, "name": "Наличные", "currency_id": "BYN",
               "income": 300.0, "expense": 120.0, "net": 180.0, "transactions_count": 12 } ],
  "total": 180.0 }

// GET /api/analytics/matrix?months=6&type=expense
{ "months": ["2025-05", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10"],
  "rows": [ { "category_id": 7, "name": "Еда и напитки", "color": "#e0913c", "icon": "utensils",
              "values": [0.0, 0.0, 12.5, 340.0, 512.1, 609.4],
              "trends": [0, 0, 0, 100, 50.6, 19.0] } ] }
```

```jsonc
// GET /api/finance/accounts/{id}/summary
{ "account_id": 3, "name": "Наличные", "currency_id": "BYN", "balance": 370.0,
  "income": 300.0, "expense": 120.0, "net": 180.0, "transactions_count": 12,
  "start_date": "...", "end_date": "..." }

// GET /api/finance/categories/tree
[ { "id": 1, "name": "Еда и напитки", "type": "expense", "icon": "utensils", "color": "#e0913c",
    "parent_id": null, "transactions_count": 42, "children": [
      { "id": 9, "name": "Продукты", "icon": "shopping-cart", "color": "#3aa76d",
        "parent_id": 1, "transactions_count": 18, "children": [] } ] } ]

// GET /api/finance/currencies/rates?base=BYN
[ { "code": "USD", "name": "US Dollar", "symbol": "$", "rate": 2.97,
    "is_base": false, "is_custom": false } ]
// rate = "how much of this currency per 1 base unit"

// GET /api/finance/tags/
[ { "id": 4, "name": "Отпуск", "color": "#6366f1", "transactions_count": 12 } ]

// GET /api/finance/templates/
[ { "id": 2, "name": "Кофе", "type": "expense", "amount": 3.5, "currency_id": "BYN",
    "account_id": 3, "category_id": 9, "note": "Кофе по утрам", "icon": "bolt",
    "usage_count": 7, "tags": [ { "id": 4, "name": "Отпуск", "color": "#6366f1" } ] } ]

// GET /api/finance/rules/
[ { "id": 1, "name": "Пятёрочка → Продукты", "is_active": true, "priority": 10,
    "field": "note", "operator": "contains", "value": "пятёрочка",
    "set_category_id": 9, "add_tag_id": null, "exclude_from_statistics": false,
    "category_name": "Продукты", "tag_name": null } ]

// POST /api/finance/rules/apply?dry_run=true
{ "matched_rules": [1], "updated_transactions": 14, "dry_run": true }
```



---

## 4. Changes to existing endpoints (backward compatibility preserved)

| Endpoint | Before | After |
|---|---|---|
| `GET /accounts` | `include_archived` | plus `include_excluded` (default `true`) |
| `GET /accounts/balance` | sum of all active accounts | `total` and an `accounts` breakdown in the base currency; only active **and not excluded from statistics** accounts are counted |
| `GET /transactions` | 5 filters, pagination | plus multi-filters, search, amount range, sorting, `X-Total-Count` |
| `GET /transactions/{id}` | `TransactionResponse` | `TransactionWithDetails` (the edit dialog is filled from these fields) |
| `GET /categories` | flat list | unchanged; the tree is a separate endpoint |

New fields in the models:
- migration `b7c1d2e3f4a5` — `accounts.is_excluded`, `users.base_currency`, `users.locale`, `users.theme`;
- migration `ecc55b6d008f` — `transactions.is_excluded`, tables `tags`, `transaction_tags`,
  `templates`, `template_tags`, `rules`, `user_currency_rates`;

Old filters and fields were not removed: `?account_id=`, `?category_id=`, `?transaction_type=`
still work alongside the new multi-value variants.

---

## 5. Access rights

The service rule is unchanged: financial data is visible only to its owner, and only a superuser
can modify the currency catalog. The added endpoints follow the same
`FinancePermission` actions:

- `me`, `summary`, `tree`, `stats`, `transactions/*`, `tags/*`, `templates/*`, `rules/*` — only
  the authenticated data owner (ownership checks remain in the services via
  `_get_owned_account`/`_get_owned_category`/`ensure_tags_owned`);
- `analytics/*` — a separate `AnalyticsPermission`: there are no public reports, all aggregates are computed
  for the `user_id` from the session;
- `currencies/rates` — public, like reading the catalog; personal rates (`PUT`/`DELETE .../rate`)
  require login;
- `DELETE /api/users/me` requires password confirmation in the request body so an accidental call
  doesn't wipe the account.

---

## 6. Errors

| Code | When |
|---|---|
| `400` | invalid date range, unknown currency, amount out of bounds, wrong password, someone else's tag/category in a template or rule |
| `401` | not authenticated |
| `403` | someone else's data, editing the currency catalog without permission |
| `404` | account/category/record not found or belongs to another user |
| `409` | category in use by records, currency in use by accounts, uniqueness conflict (including tag name) |
| `422` | schema failed pydantic validation |

---

## 7. What is covered by tests

The new code is covered by dedicated suites; full run — `pytest tests`.

```
$ ENVIRONMENT=TEST pytest tests -q
173 passed
```

| Suite | Tests | What it checks |
|---|---|---|
| `tests/analytics/test_analytics.py` | 16 | aggregates: totals, period comparison, currency conversion, excluded accounts and records, cashflow and balance charts, category and account shares, the "categories × months" report |
| `tests/finance/test_tags.py` | 11 | tag CRUD, name uniqueness, isolation, attaching to records, filtering by tags, deletion without losing records |
| `tests/finance/test_templates.py` | 8 | template CRUD, applying with balance recomputation, copying tags, reference validation |
| `tests/finance/test_rules.py` | 16 | condition operators, auto-categorization on creation, tagging by rule, hiding from statistics, priorities, running over existing records and dry-run |
| `tests/finance/test_user_rates.py` | 10 | personal rate in calculations, isolation between users, reset to the catalog, validation |
| `tests/finance/test_listing.py`, `test_router_extra.py`, `tests/users/test_profile.py` | 48 | record listings, HTTP level, profile (written in the previous iteration) |

The tests require PostgreSQL — the same as the rest of the suite: the database is created and dropped by the
`test_db` fixture. Migrations were verified on a separate database: `alembic upgrade head` → `downgrade base` →
`upgrade head` passes without errors.

---

## 8. What is left out of scope

Of the list that used to be here, everything has been implemented except one item.

**Bank synchronization** is the only unimplemented feature. It requires integration with
a bank API (or an aggregator like Plaid): OAuth connection, statement import, transaction
deduplication, background sync jobs. The "lock" on the account card also depends on it.
The current data model has no fields for this, and I chose not to add them "just in case".

The app is completely free: billing and paid limits have been removed, all features are available
to every user.

## 9. Screen-to-endpoint mapping

A cross-check of what the frontend actually calls after being connected to the API
(mock data remains only in the `/design` component showcase).

| Screen | Requests |
|---|---|
| `/login` | `POST /api/auth/login`, `GET /api/users/me` |
| `/` (Overview) | `GET /api/finance/accounts/`, `GET /api/analytics/summary`, `GET /api/analytics/timeseries` (balance and cashflow), `GET /api/analytics/by-category` |
| `/accounts` | `GET /api/finance/accounts/`, `POST`, `PATCH /{id}`, `DELETE /{id}` |
| `/accounts/{id}` | `GET /api/finance/accounts/`, `GET /api/analytics/by-account`, `GET /api/analytics/timeseries?metric=balance`, `GET /api/finance/transactions/?account_ids=…`, `POST /transactions/bulk-delete` (deleting duplicates) |
| `/records` | `GET /api/finance/transactions/` (filters, sorting, `X-Total-Count`), `POST`, `PATCH`, `DELETE`, `POST /transactions/bulk-delete`, `GET /transactions/export?format=csv\|json`, `POST /transactions/import` |
| `/analytics` | `GET /api/analytics/matrix`, `/summary`, `/timeseries`, `/by-category`, `/by-account` |
| `/settings` | `GET`/`PATCH /api/users/me`, `GET /api/finance/currencies/rates` |
| `/settings/currencies` | `GET /api/finance/currencies/rates`, `PUT`/`DELETE /api/finance/currencies/{code}/rate` |
| `/settings/categories` | `GET /api/finance/categories/tree`, `POST`, `PATCH /{id}`, `DELETE /{id}` |
| `/settings/tags` | `GET`/`POST`/`PATCH`/`DELETE /api/finance/tags` |
| `/settings/templates` | `GET`/`POST`/`DELETE /api/finance/templates`, `POST /{id}/apply` |
| `/settings/rules` | `GET`/`POST`/`PATCH`/`DELETE /api/finance/rules`, `POST /rules/apply` |
| `/settings/privacy` | `GET /api/users/me/export`, `DELETE /api/users/me` |

Checks without a browser (requires a running backend with demo data):

```bash
bash tools/smoke-api.sh          # read endpoints of all screens
python3 tools/smoke_write.py     # writes: record, tag, template, rule, profile
```
