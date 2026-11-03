# Контракт API под фронтенд «Трекер финансов»

Документ составлен по факту того, что реально рисует фронтенд (`frontend/src/__pages__`),
а не по «хорошо бы иметь». Для каждого экрана перечислено, какие данные он показывает,
какой эндпоинт это закрывает и существует ли он уже в сервисе.

Обозначения: ✅ — уже было в сервисе, ➕ — добавлено в этой итерации.

Базовые префиксы: `/api/finance` — финансы, `/api/users` — профиль, `/api/analytics` —
аналитика (отдельное приложение), `/api/billing` — тарифы и платежи (отдельное приложение).
Аутентификация: cookie `access_token` (как в существующем `CurrentUser`), ошибки — стандартные
`401/403/404/422`.

---

## 1. Экраны и их данные

### 1.1 «Вход» (`/login`)

| Что нужно | Эндпоинт | Статус |
|---|---|---|
| Войти по email и паролю | `POST /api/auth/login` | ✅ |
| Регистрация | `POST /api/auth/register` | ✅ |
| Подтверждение почты | `POST /api/auth/send-verification-email`, `POST /api/auth/verify-email` | ✅ |
| Выход | `POST /api/auth/logout` | ✅ |
| Кто я (шапка, меню пользователя) | `GET /api/users/me` | ➕ |

### 1.2 «Обзор» (`/`)

| Что нужно | Эндпоинт | Статус |
|---|---|---|
| Карточки счетов с балансами | `GET /api/finance/accounts` | ✅ |
| Общий баланс в базовой валюте | `GET /api/finance/accounts/balance` | ✅ (учитывает исключённые — исправлено) |
| Доходы/расходы/нетто за период + сравнение с прошлым | `GET /api/analytics/summary` | ➕ |
| График денежного потока по дням | `GET /api/analytics/timeseries?metric=cashflow` | ➕ |
| График баланса | `GET /api/analytics/timeseries?metric=balance` | ➕ |
| Кольцевая структура расходов | `GET /api/analytics/by-category` | ➕ |
| Сравнение периодов | `GET /api/analytics/summary?compare=true` | ➕ |

### 1.3 «Счета» (`/accounts`) и карточка счёта (`/accounts/:id`)

| Что нужно | Эндпоинт | Статус |
|---|---|---|
| Список, в т.ч. архивные | `GET /api/finance/accounts?include_archived=` | ✅ |
| Создать / изменить / удалить | `POST`, `PATCH`, `DELETE /api/finance/accounts/{id}` | ✅ |
| Архивировать / вернуть | `POST /api/finance/accounts/{id}/archive` | ✅ |
| «Исключено из статистики» | `POST /api/finance/accounts/{id}/exclude` | ➕ |
| Сводка по счёту: доходы, расходы, операции | `GET /api/finance/accounts/{id}/summary` | ➕ |
| Записи счёта | `GET /api/finance/transactions?account_ids=` | ✅/➕ (мультивыбор) |
| Экспорт записей счёта | `GET /api/finance/transactions/export?format=&account_ids=` | ➕ |

«Замок» на карточках счетов (Alfa RUB, Tinkoff) — признак синхронизации с банком. В сервисе
синхронизации нет, поэтому отдельного поля не вводим: фронтенд рисует замок по наличию флага
`is_locked`, который пока отдаётся `false` — так экран не ломается, а ложных данных нет.

### 1.4 «Записи» (`/records`)

| Что нужно | Эндпоинт | Статус |
|---|---|---|
| Список с фильтрами и пагинацией | `GET /api/finance/transactions` | ✅/➕ (расширен) |
| Фильтры: счета, категории, валюты, типы — множественным выбором | `account_ids`, `category_ids`, `currency_ids`, `types` | ➕ |
| Поиск по заметке, категории, счёту | `q` | ➕ |
| Диапазон суммы | `amount_min`, `amount_max` | ➕ |
| Сортировка (дата, сумма) | `sort` | ➕ |
| Общее количество записей для «показать ещё» | заголовок `X-Total-Count` | ➕ |
| Создать / изменить / удалить | `POST`, `PATCH`, `DELETE` | ✅ |
| Массовое удаление выбранных | `POST /api/finance/transactions/bulk-delete` | ➕ |
| Экспорт CSV / JSON за период | `GET /api/finance/transactions/export` | ➕ |
| Сводка по категориям за период | `GET /api/finance/transactions/summary` | ✅ |

Карточка записи отдаёт `TransactionWithDetails` — с названием и цветом категории, именем счёта и
символом валюты: без этого диалог редактирования не заполнить.

### 1.5 «Аналитика» (`/analytics`)

| Что нужно | Эндпоинт | Статус |
|---|---|---|
| Итоги за период и сравнение | `GET /api/analytics/summary` | ➕ |
| Отчёт «категории × месяцы» | `GET /api/analytics/matrix` | ➕ |
| Разбивка по категориям и подкатегориям | `GET /api/analytics/by-category` | ➕ |
| Разбивка по счетам | `GET /api/analytics/by-account` | ➕ |
| Динамика по дням/неделям/месяцам | `GET /api/analytics/timeseries` | ➕ |

Аналитика вынесена в отдельное приложение (`src/analytics/`) и живёт под своим префиксом
`/api/analytics`: это read-model над финансовыми данными, у него нет CRUD и своей записи в БД.

### 1.6 «Настройки» (`/settings` и разделы)

| Экран | Что нужно | Эндпоинт | Статус |
|---|---|---|---|
| Профиль | Читать и править имя, почту, язык, часовой пояс, базовую валюту | `GET`, `PATCH /api/users/me` | ➕ |
| Профиль | Сменить пароль | `POST /api/users/me/password` | ➕ |
| Профиль | Аватар | `PATCH /api/users/me` (поле `photo`) | ➕ |
| Валюты | Список валют с курсами | `GET /api/finance/currencies` | ✅ |
| Валюты | Курсы относительно выбранной базовой | `GET /api/finance/currencies/rates?base=BYN` | ➕ |
| Валюты | Правка курса в справочнике | `PATCH /api/finance/currencies/{code}` | ✅ (только суперпользователь) |
| Валюты | Личный курс для своих расчётов | `PUT`, `DELETE /api/finance/currencies/{code}/rate` | ➕ |
| Категории | Дерево: категория → подкатегории со счётчиками | `GET /api/finance/categories/tree` | ➕ |
| Категории | Сколько записей и на какую сумму | `GET /api/finance/categories/stats` | ➕ |
| Категории | CRUD, подкатегории через `parent_id` | `GET/POST/PATCH/DELETE /api/finance/categories` | ✅ |
| Приватность | Скачать свои данные | `GET /api/users/me/export` | ➕ |
| Приватность | Удалить аккаунт | `DELETE /api/users/me` | ➕ |
| Метки | Список меток со счётчиками, CRUD | `GET/POST/PATCH/DELETE /api/finance/tags` | ➕ |
| Шаблоны | Список и CRUD шаблонов быстрого ввода | `GET/POST/PATCH/DELETE /api/finance/templates` | ➕ |
| Шаблоны | Создать запись по шаблону | `POST /api/finance/templates/{id}/apply` | ➕ |
| Правила | Список и CRUD правил авто-категоризации | `GET/POST/PATCH/DELETE /api/finance/rules` | ➕ |
| Правила | Применить правила к существующим записям | `POST /api/finance/rules/apply` | ➕ |
| Тарифы и платежи | Каталог тарифов | `GET /api/billing/plans` | ➕ |
| Тарифы и платежи | Текущая подписка, оформление, отмена | `GET/POST/DELETE /api/billing/subscription` | ➕ |
| Тарифы и платежи | Способы оплаты | `GET/POST/DELETE /api/billing/payment-methods` | ➕ |
| Тарифы и платежи | История платежей | `GET /api/billing/payments` | ➕ |
| Тарифы и платежи | Доступные провайдеры | `GET /api/billing/providers` | ➕ |

### 1.7 Что фронтенд делает сам

- Экспорт CSV/TSV/XLS/JSON/PDF — сейчас на клиенте из уже загруженных данных, PDF — печатью
  браузера. Серверный экспорт (`/transactions/export`) нужен только для выгрузки периода,
  который не влезает в страницу; формат PDF на сервере не делаем (нет генератора в зависимостях).
- Тема и язык интерфейса — хранятся в `localStorage`; на сервере лежит только предпочтение
  пользователя (`locale`), чтобы новые устройства стартовали с него.
- Все графики строятся на клиенте из агрегатов; сервер отдаёт только числа.

---

## 2. Добавленные эндпоинты: полный список

### Профиль

```
GET    /api/users/me                    → User
PATCH  /api/users/me                    → User           (firstname, lastname, email, photo, timezone,
                                                          locale, theme, base_currency)
POST   /api/users/me/password           → 204            (old_password, new_password)
GET    /api/users/me/export             → JSON-архив     (счета, категории, записи, подписки, курсы)
DELETE /api/users/me                    → 204            (тело: {"password": "..."} — каскадное удаление)
```

### Счета

```
POST   /api/finance/accounts/{id}/exclude?is_excluded=true → AccountResponse
GET    /api/finance/accounts/{id}/summary?start_date&end_date → AccountSummary
GET    /api/finance/accounts/balance                       → BalanceOverview (без исключённых)
```

### Категории

```
GET    /api/finance/categories/tree?category_type=expense&start_date&end_date → List[CategoryNode]
GET    /api/finance/categories/stats?category_type&start_date&end_date        → List[CategoryStat]
```

### Записи

```
GET    /api/finance/transactions?account_ids=1&account_ids=2&category_ids=&currency_ids=&types=&
                             q=&amount_min=&amount_max=&start_date=&end_date=&sort=&
                             with_total=true&offset=&limit=
                                                          → List[TransactionWithDetails] + X-Total-Count
                                                          sort: date_desc | date_asc | amount_desc | amount_asc
POST   /api/finance/transactions/bulk-delete              → {deleted: int, missing: [int]}
                                                          тело: {"ids": [1, 2, 3]}
GET    /api/finance/transactions/export?format=csv|json&… → файл (до 5000 записей)
```

### Аналитика (отдельное приложение, префикс `/api/analytics`)

```
GET /api/analytics/summary?start_date&end_date&compare=true      → AnalyticsSummary
GET /api/analytics/timeseries?start_date&end_date&group_by=day|week|month&metric=cashflow|balance
GET /api/analytics/by-category?start_date&end_date&transaction_type=expense&parent_id&
                               include_children=true&rollup=false
GET /api/analytics/by-account?start_date&end_date
GET /api/analytics/matrix?months=6&transaction_type=expense&rollup=true&end_date
```

### Валюты и личные курсы

```
GET /api/finance/currencies/rates?base=BYN                → List[CurrencyRate]
PUT /api/finance/currencies/{code}/rate                   → CurrencyRate   (тело: {"rate": 2.5})
DELETE /api/finance/currencies/{code}/rate                → 204
```

`base` по умолчанию BYN — как базовая валюта сервиса. Неизвестный код → `400` (молча
подставлять другую валюту нельзя: курс тогда посчитается неверно).

`/rates` публичный: справочник не является личными данными. Если пользователь авторизован,
в ответе учитываются его личные курсы — у них `is_custom: true`. `PUT`/`DELETE` требуют входа:
справочник общий, а личный курс принадлежит пользователю.

### Метки

```
GET    /api/finance/tags/                → List[TagResponse] (+transactions_count)
POST   /api/finance/tags/                → TagResponse   (name, color)
GET    /api/finance/tags/{tag_id}        → TagResponse
PATCH  /api/finance/tags/{tag_id}        → TagResponse
DELETE /api/finance/tags/{tag_id}        → 204          (связи с записями уходят, записи остаются)

GET /api/finance/transactions?tag_ids=1&tag_ids=2        → записи хотя бы с одной из меток
POST /api/finance/transactions/  {"tag_ids": [1, 2]}     → метки вешаются при создании
PATCH /api/finance/transactions/{id} {"tag_ids": []}     → пустой список снимает все метки
```

### Шаблоны быстрого ввода

```
GET    /api/finance/templates/                 → List[TemplateResponse] (популярные сверху)
POST   /api/finance/templates/                 → TemplateResponse
GET    /api/finance/templates/{template_id}    → TemplateResponse
PATCH  /api/finance/templates/{template_id}    → TemplateResponse
DELETE /api/finance/templates/{template_id}    → 204
POST   /api/finance/templates/{template_id}/apply?date=…   → TransactionResponse
```

`apply` создаёт запись тем же сервисом, что и обычное создание: срабатывают правила и
пересчитывается баланс счёта, а `usage_count` шаблона увеличивается на единицу.

### Правила авто-категоризации

```
GET    /api/finance/rules/              → List[RuleResponse] (по возрастанию priority)
POST   /api/finance/rules/              → RuleResponse
GET    /api/finance/rules/{rule_id}     → RuleResponse
PATCH  /api/finance/rules/{rule_id}     → RuleResponse
DELETE /api/finance/rules/{rule_id}     → 204
POST   /api/finance/rules/apply?start_date&end_date&dry_run=false → RuleApplyResult
```

Условие: `field` = `note` | `amount`, `operator` = `contains` | `equals` | `greater` | `less`.
Действия (можно несколько сразу): `set_category_id`, `add_tag_id`, `exclude_from_statistics`.

Правила применяются при создании записи и при вызове `apply`. Скрытые из статистики записи
остаются в списках — у них `is_excluded: true`, и агрегаты их не учитывают.

### Биллинг (отдельное приложение, префикс `/api/billing`)

```
GET    /api/billing/plans                                  → List[PlanResponse]      (публичный)
GET    /api/billing/providers                              → List[ProviderInfo]      (публичный)
GET    /api/billing/subscription                           → SubscriptionResponse
POST   /api/billing/subscription                           → CheckoutSession
DELETE /api/billing/subscription?immediately=false         → SubscriptionResponse
GET    /api/billing/payment-methods                        → List[PaymentMethodResponse]
POST   /api/billing/payment-methods                        → PaymentMethodResponse
POST   /api/billing/payment-methods/{method_id}/default    → PaymentMethodResponse
DELETE /api/billing/payment-methods/{method_id}            → 204
GET    /api/billing/payments?offset&limit                  → List[PaymentResponse]
POST   /api/billing/webhooks/{provider_code}               → {"status": "succeeded"}  (вебхук провайдера)
```

---

## 3. Форматы ответов

Все суммы — в базовой валюте пользователя, округление до 2 знаков. Курс берётся из
личных настроек валют (`user_currency_rates`), а при их отсутствии — из справочника
`currencies`. Периоды — ISO-8601, `start_date`/`end_date` валидируются через уже
существующий `normalize_period`.

```jsonc
// GET /api/analytics/summary?start_date=2025-10-01&end_date=2025-10-31&compare=true
{
  "start_date": "2025-10-01T00:00:00",
  "end_date": "2025-10-31T23:59:59",
  "income": 12267.07,
  "expense": 3329.15,
  "net": 8937.92,
  "transactions_count": 148,
  "previous": {                      // null, если compare=false
    "start_date": "...", "end_date": "...",
    "income": 8297.03, "expense": 3510.44, "net": 4786.59, "transactions_count": 121
  },
  "change": {                        // проценты к предыдущему периоду
    "income": 47.85, "expense": -5.17, "net": 86.72
  }
}
```

```jsonc
// GET /api/analytics/timeseries?metric=cashflow&group_by=day
{ "group_by": "day", "metric": "cashflow", "points": [
    { "date": "2025-10-01T00:00:00", "income": 1200.0, "expense": 400.0, "net": 800.0 } ] }

// metric=balance — накопительный остаток по всем счетам на конец интервала
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
// rate = «сколько этой валюты за 1 базовую»

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

```jsonc
// GET /api/billing/plans  (публичный)
[ { "code": "free", "name": "Бесплатный", "price": 0.0, "currency": "USD", "period": "none",
    "features": ["1 счёт", "5 категорий", "отчёты за месяц"], "is_active": true },
  { "code": "monthly", "name": "Месячный", "price": 4.99, "currency": "USD", "period": "month",
    "features": ["неограниченно счетов", "аналитика"], "is_active": true } ]

// GET /api/billing/providers
[ { "code": "mock", "title": "Тестовая оплата (мок)", "methods": ["card", "crypto"],
    "is_configured": true, "is_default": true, "is_mock": true },
  { "code": "stripe", "title": "Банковская карта (Stripe)", "methods": ["card"],
    "is_configured": false, "is_default": false, "is_mock": false } ]

// GET /api/billing/subscription  (без подписки — бесплатный тариф)
{ "id": null, "plan_code": "free", "plan_name": "Бесплатный", "status": "active",
  "started_at": null, "current_period_end": null, "cancel_at_period_end": false, "provider": "mock" }

// POST /api/billing/subscription  {"plan_code": "monthly"}
{ "payment_id": 12, "status": "succeeded", "provider": "mock",
  "provider_reference": "mock_1a2b3c4d5e6f7788", "checkout_url": null,
  "requires_redirect": false,
  "subscription": { "id": 3, "plan_code": "monthly", "plan_name": "Месячный", "status": "active",
                    "started_at": "2025-11-02T19:00:00", "current_period_end": "2025-12-02T19:00:00",
                    "cancel_at_period_end": false, "provider": "mock" } }

// Бесплатный тариф: не больше двух незаархивированных счетов и только базовая
// валюта. Создание третьего счёта, счёта в другой валюте, записи/шаблона в
// другой валюте и личного курса не-базовой валюты возвращает 402. Ранее
// созданные счета не удаляются: они отдаются с is_locked=true и lock_reason
// ("subscription_required_currency" / "subscription_required_account_limit")
// и доступны только для чтения и архивации до возобновления подписки.

// GET /api/billing/payments
[ { "id": 12, "plan_code": "monthly", "kind": "subscription", "amount": 4.99, "currency": "USD",
    "status": "succeeded", "provider": "mock", "failure_reason": null, "created_at": "..." } ]
```

---

## 4. Изменения в существующих эндпоинтах (обратная совместимость сохранена)

| Эндпоинт | Было | Стало |
|---|---|---|
| `GET /accounts` | `include_archived` | плюс `include_excluded` (по умолчанию `true`) |
| `GET /accounts/balance` | сумма всех активных счетов | `total` и разбивка `accounts` в базовой валюте; учитываются только активные **и не исключённые из статистики** счета, у счетов есть `is_locked`/`lock_reason` |
| `GET /transactions` | 5 фильтров, пагинация | плюс мультифильтры, поиск, диапазон суммы, сортировка, `X-Total-Count` |
| `GET /transactions/{id}` | `TransactionResponse` | `TransactionWithDetails` (диалог редактирования заполняется по этим полям) |
| `GET /categories` | плоский список | без изменений; дерево — отдельным эндпоинтом |

Новые поля в моделях:
- миграция `b7c1d2e3f4a5` — `accounts.is_excluded`, `users.base_currency`, `users.locale`, `users.theme`;
- миграция `ecc55b6d008f` — `transactions.is_excluded`, таблицы `tags`, `transaction_tags`,
  `templates`, `template_tags`, `rules`, `user_currency_rates`;
- миграция `f1a2b3c4d5e6` — таблицы биллинга `plans`, `plan_subscriptions`, `payment_methods`,
  `payments` и сид каталога тарифов.

Старые фильтры и поля не удалялись: `?account_id=`, `?category_id=`, `?transaction_type=`
по-прежнему работают рядом с новыми множественными вариантами.

---

## 5. Права доступа

Правило сервиса прежнее: финансовые данные видны только владельцу, справочник валют
меняет только суперпользователь. Добавленные эндпоинты следуют тем же действиям
`FinancePermission`:

- `me`, `summary`, `tree`, `stats`, `transactions/*`, `tags/*`, `templates/*`, `rules/*` — только
  аутентифицированный владелец данных (проверка владения остаётся в сервисах через
  `_get_owned_account`/`_get_owned_category`/`ensure_tags_owned`);
- `analytics/*` — отдельное `AnalyticsPermission`: публичных отчётов нет, все агрегаты считаются
  по `user_id` из сессии;
- `currencies/rates` — публично, как и чтение справочника; личные курсы (`PUT`/`DELETE .../rate`)
  требуют входа;
- `billing/plans`, `billing/providers` — публично (каталог нужен до входа), остальной биллинг —
  только владелец подписки и способов оплаты;
- `DELETE /api/users/me` требует подтверждения паролем в теле запроса, чтобы случайный вызов
  не снёс аккаунт.

---

## 6. Ошибки

| Код | Когда |
|---|---|
| `400` | неверный диапазон дат, неизвестная валюта, сумма вне допустимого, неверный пароль, чужая метка/категория в шаблоне или правиле, неверная подпись вебхука |
| `401` | нет аутентификации |
| `403` | чужие данные, правка справочника валют без прав |
| `404` | счёт/категория/запись не найдены или принадлежат другому пользователю |
| `409` | категория занята записями, валюта занята счетами, конфликт уникальности (в том числе имя метки) |
| `503` | выбранный платёжный провайдер не настроен (нет ключей) |
| `422` | схема не прошла валидацию pydantic |

---

## 7. Что проверено тестами

Новый код покрыт отдельными наборами; полный прогон — `pytest tests`.

```
$ ENVIRONMENT=TEST pytest tests -q
176 passed
```

| Набор | Тестов | Что проверяет |
|---|---|---|
| `tests/analytics/test_analytics.py` | 16 | агрегаты: итоги, сравнение периодов, конвертация валют, исключённые счета и записи, графики денежного потока и остатка, доли категорий и счетов, отчёт «категории × месяцы» |
| `tests/billing/test_billing.py` | 19 | каталог тарифов, провайдеры, оформление и отмена подписки, мок-оплата, отказ при ненастроенном провайдере, способы оплаты, история платежей, вебхуки |
| `tests/finance/test_tags.py` | 11 | CRUD меток, уникальность имени, изоляция, привязка к записям, фильтр по меткам, удаление без потери записей |
| `tests/finance/test_templates.py` | 8 | CRUD шаблонов, применение с пересчётом баланса, копирование меток, валидация ссылок |
| `tests/finance/test_rules.py` | 16 | операторы условий, авто-категоризация при создании, метки правилом, скрытие из статистики, приоритеты, прогон по существующим записям и dry-run |
| `tests/finance/test_user_rates.py` | 10 | личный курс в расчётах, изоляция между пользователями, сброс к справочнику, валидация |
| `tests/finance/test_listing.py`, `test_router_extra.py`, `tests/users/test_profile.py` | 48 | выборки записей, HTTP-уровень, профиль (написаны в предыдущей итерации) |

Тесты требуют PostgreSQL — тот же, что и остальной набор: база создаётся и удаляется фикстурой
`test_db`. Миграции проверены на отдельной базе: `alembic upgrade head` → `downgrade base` →
`upgrade head` проходит без ошибок, сид тарифов создаёт три записи.

---

## 8. Что осталось за продуктом

Из списка, который был здесь раньше, реализовано всё, кроме одного пункта.

**Синхронизация с банком** — единственная нереализованная фича. Она требует интеграции с
банковским API (или агрегатором вроде Plaid): OAuth-подключение, импорт выписок, дедупликация
операций, фоновые задачи синхронизации. От неё же зависит «замок» на карточке счёта
(`is_locked` на фронтенде): блокировка имеет смысл только когда записи приходят извне.
В текущей модели данных полей под это нет, и добавлять их «на всякий случай» не стал.

**Мок-оплата вместо реальной.** Провайдер `mock` всегда подтверждает платёж — это осознанное
решение: без ключей эквайринга реальную оплату не проверить. Архитектура готова принимать
внешнего провайдера: интерфейс `PaymentProvider` (`src/billing/providers/base.py`), реестр
провайдеров, эндпоинт вебхуков и проверка подписи. Подключение Stripe или крипто-процессинга
сводится к реализации четырёх методов в классе провайдера и заполнению переменных окружения
(`BILLING_PROVIDER`, `STRIPE_SECRET_KEY`, `CRYPTO_API_KEY`); сервис, схемы и API не меняются.

Заглушки `StripePaymentProvider` и `CryptoPaymentProvider` намеренно бросают
`NotImplementedError`, а биллинг превращает это в `503` и помечает платёж как `failed`:
выдать подписку без оплаты нельзя.

## 9. Соответствие экранов и эндпоинтов

Сверка того, что фронтенд действительно вызывает после подключения к API
(мок-данные остались только на витрине компонентов `/design`).

| Экран | Запросы |
|---|---|
| `/login` | `POST /api/auth/login`, `GET /api/users/me` |
| `/` (Обзор) | `GET /api/finance/accounts/`, `GET /api/analytics/summary`, `GET /api/analytics/timeseries` (balance и cashflow), `GET /api/analytics/by-category` |
| `/accounts` | `GET /api/finance/accounts/`, `POST`, `PATCH /{id}`, `DELETE /{id}` |
| `/accounts/{id}` | `GET /api/finance/accounts/`, `GET /api/analytics/by-account`, `GET /api/analytics/timeseries?metric=balance`, `GET /api/finance/transactions/?account_ids=…`, `POST /transactions/bulk-delete` (удаление дубликатов) |
| `/records` | `GET /api/finance/transactions/` (фильтры, сортировка, `X-Total-Count`), `POST`, `PATCH`, `DELETE`, `POST /transactions/bulk-delete`, `GET /transactions/export?format=csv\|json` |
| `/analytics` | `GET /api/analytics/matrix`, `/summary`, `/timeseries`, `/by-category`, `/by-account` |
| `/settings` | `GET`/`PATCH /api/users/me`, `GET /api/finance/currencies/rates` |
| `/settings/currencies` | `GET /api/finance/currencies/rates`, `PUT`/`DELETE /api/finance/currencies/{code}/rate` |
| `/settings/categories` | `GET /api/finance/categories/tree`, `POST`, `PATCH /{id}`, `DELETE /{id}` |
| `/settings/tags` | `GET`/`POST`/`PATCH`/`DELETE /api/finance/tags` |
| `/settings/templates` | `GET`/`POST`/`DELETE /api/finance/templates`, `POST /{id}/apply` |
| `/settings/rules` | `GET`/`POST`/`PATCH`/`DELETE /api/finance/rules`, `POST /rules/apply` |
| `/settings/payments` | `GET /api/billing/plans`, `/providers`, `/subscription`, `/payment-methods`, `/payments`, `POST /subscription`, `POST`/`DELETE /payment-methods` |
| `/settings/privacy` | `GET /api/users/me/export`, `DELETE /api/users/me` |

Проверки без браузера (нужен поднятый backend с демо-данными):

```bash
bash tools/smoke-api.sh          # читающие эндпоинты всех экранов
python3 tools/smoke_write.py     # запись: запись, метка, шаблон, правило, подписка, профиль
```
