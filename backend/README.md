# BudgetTracker backend

Микросервис личного бюджета на FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL.

## Структура проекта

Каждый домен описан отдельным приложением внутри `src/` и повторяет одну и ту же
слоистую структуру (эталон — `src/users/`):

| Слой | Файл | Ответственность |
| --- | --- | --- |
| Модели | `models.py` | Таблицы SQLAlchemy, связи и ограничения |
| Схемы | `schemas.py` | Pydantic-схемы запросов и ответов (Base/Create/Update/Response/Inline) |
| Доступ к данным | `dao.py` | Запросы к БД на основе `BaseDAO` |
| Бизнес-логика | `service.py` | Правила домена на основе `BaseService`, права владельца, транзакции |
| Права | `permissions.py` | Класс прав для ViewSet-ов |
| Представление | `viewsets.py` | Оркестрация сервисов, декоратор `check_permissions` |
| HTTP | `router.py` | Роутеры, зависимости, коды ответов |
| Зависимости/утилиты | `dependencies.py`, `utils.py` | FastAPI-зависимости и доменные хелперы |

Общий каркас лежит в корне `src/`: `dao.py`, `service.py`, `viewset.py`,
`permissions.py`, `exceptions.py`, `database.py`.

## Домены

### `src/users/`

Пользователи, аутентификация (JWT в cookie), сессии обновления токенов,
подтверждение email.

### `src/finance/`

Финансовый домен:

- **Счета** (`/api/finance/accounts`) — CRUD, архивация, сводный баланс в базовой валюте
  (`GET /api/finance/accounts/balance`).
- **Категории** (`/api/finance/categories`) — CRUD с поддержкой подкатегорий;
  тип подкатегории должен совпадать с родительской, удаление занятой категории запрещено.
- **Транзакции** (`/api/finance/transactions`) — CRUD с автоматическим пересчётом баланса
  счёта, конвертацией по курсу валюты и аналитикой (`GET /api/finance/transactions/summary`).
- **Подписки** (`/api/finance/subscriptions`) — регулярные платежи на базе транзакции,
  ближайшие списания (`GET /api/finance/subscriptions/upcoming`), перенос даты платежа
  (`POST /api/finance/subscriptions/{id}/advance`).
- **Валюты** (`/api/finance/currencies`) — справочник; чтение публичное, изменение доступно
  только суперпользователю.

- **Метки, шаблоны, правила** (`/api/finance/tags`, `/templates`, `/rules`) — метки записей,
  шаблоны быстрого ввода (`POST /templates/{id}/apply`) и правила авто-категоризации
  (`POST /rules/apply` с `dry_run`).

Все финансовые данные изолированы по владельцу: любой запрос фильтруется по `user_id`
текущего пользователя, чужой объект возвращает `404`.

### `src/analytics/`

Отдельное приложение аналитики (§8 документа): `GET /api/analytics/summary` (итоги и сравнение
с предыдущим периодом), `timeseries` (денежный поток и остаток), `by-category`, `by-account`,
`matrix` (месяцы × категории). Считает на стороне БД, кэширует справочники и не зависит
от `finance` — обратное тоже верно.

### `src/billing/`

Тарифы и оплата: `GET /api/billing/plans`, `providers`, `subscription`, `payment-methods`,
`payments`. Провайдеры выбираются реестром (`mock`, `stripe`, `crypto`); неподключённый
провайдер отвечает `503`, а платёж помечается `failed` — тихого отката на mock нет.
Реальный интернет-эквайринг подключается реализацией провайдера, без изменений в сервисах.

## Запуск

Backend запускается только в составе docker-стека из корня репозитория — отдельный
запуск с хоста не поддерживается (см. корневой `README.md`):

```bash
docker compose up -d --build        # postgres + redis + backend + frontend
docker compose logs -f backend
```

Миграции контейнер применяет сам при старте (`entrypoint.sh`), схема и справочник
валют создаются автоматически. Документация API: http://localhost:8000/docs
(порт меняется переменной `BACKEND_HOST_PORT`), проверка живости: `GET /health`.

## Демо-данные

Пустая база не даёт проверить интерфейс: нет счетов и категорий, а регистрация
требует подтверждения почты. Скрипт создаёт готовый набор и сразу проверенного
пользователя:

```bash
docker compose exec backend python -m scripts.seed_demo            # 6 счетов, 25 категорий, 387 записей
docker compose exec backend python -m scripts.seed_demo --reset    # удалить данные и засеять заново
```

Доступы печатает сам скрипт, переопределяются через `DEMO_USER_EMAIL` и
`DEMO_USER_PASSWORD`.

## Администратор

Управленческая учётная запись с правами суперпользователя (например, правка
справочника валют — обычному пользователю она недоступна). Логин и пароль
стандартные и одинаковы на любой машине:

| Логин | Пароль |
| --- | --- |
| `admin` + `@` + `budgettracker.local` | `admin12345` |

```bash
docker compose exec backend python -m scripts.seed_admin                  # создать (идемпотентно)
docker compose exec backend python -m scripts.seed_admin --keep-password  # не трогать текущий пароль
```

Скрипт идемпотентен: если пользователь уже есть, он возвращает стандартную почту
и обязательно выставляет `is_superuser`, `is_verified` и `is_active`, а также
сбрасывает пароль на стандартный — так учётку можно «починить» одной командой,
если пароль забыт или изменён. Данные админу не создаются: наполнение для
демонстрации делает `scripts.seed_demo`.

Логин и пароль переопределяются через `ADMIN_USER_EMAIL` и `ADMIN_USER_PASSWORD`
(справка — `.env.example`; в контейнер переменные попадают из `x-backend-env`,
поэтому при необходимости добавьте их в `environment` сервиса `backend`). Стандартные
значения годятся только для локальной разработки: в проде задайте свои и не
запускайте скрипт автоматически при старте контейнера.

## Миграции

`alembic/env.py` берёт URL из настроек приложения (`settings.ASYNC_DATABASE_URL`) и работает
через асинхронный движок, поэтому одни и те же переменные окружения используются и приложением,
и миграциями.

```bash
docker compose exec backend alembic upgrade head                   # применить все миграции
docker compose exec backend alembic downgrade -1                   # откатить последнюю
docker compose exec backend alembic revision --autogenerate -m ""  # создать миграцию
docker compose exec backend alembic current                        # текущая ревизия
```

В `src/migrations/versions/`:

- `eaca08a294fc` — начальная схема: `users`, `currencies`, `accounts`, `categories`,
  `transactions`, `subscriptions` (+ enum-типы, индексы, каскады);
- `7c1f0a9b2d34` — базовый справочник валют (USD, EUR, RUB, KZT, ...). Он нужен потому, что
  `accounts.currency_id` и `transactions.currency_id` ссылаются на `currencies`, а создавать
  валюты через API может только суперпользователь.

## Docker

`Dockerfile` собирает образ на `python:3.13-slim`, ставит зависимости из `poetry.lock`
(`poetry install --only main`) и запускается через `entrypoint.sh`, который перед стартом
приложения выполняет `alembic upgrade head` (отключается переменной `RUN_MIGRATIONS=false`).

Сборка с dev-зависимостями (нужно для тестов внутри контейнера):

```bash
docker compose build backend                     # образ для dev-стека (INSTALL_DEV=true)
docker build --build-arg INSTALL_DEV=true -t budgettracker-backend .
```

Актуальные команды запуска всего стека (postgres + redis + backend + frontend) описаны
в корневом `README.md` и файлах `docker-compose.yml` / `docker-compose.prod.yml`.

## Тесты

Тестам нужен живой PostgreSQL (переменные `TEST_POSTGRES_*`) и `pytest-asyncio`; тесты
запускаются в контейнере, потому что `tests/` исключён из образа и подключается
bind-mount-ом из dev-стека:

```bash
docker compose up -d postgres
docker compose exec backend python -m pytest tests -q
```

Тесты сами создают и удаляют временные БД на сервере из `TEST_POSTGRES_*`, поэтому
дополнительная настройка не нужна.

Структура тестов повторяет структуру приложений: `tests/users/`, `tests/finance/`,
`tests/analytics/`, `tests/billing/`.
