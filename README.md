# BudgetTracker

Сервис учёта личных финансов: счета, категории, транзакции и подписки с мультивалютностью.

## Технологический стек

- **Backend**: Python 3.13, FastAPI, SQLAlchemy 2.0 (async, asyncpg), Alembic, Pydantic v2
- **Database**: PostgreSQL 16
- **Cache / очереди**: Redis, RabbitMQ + Celery (опционально, см. профиль `workers`)
- **Frontend**: React 18, TypeScript, Vite 5, TailwindCSS, Recharts
- **Docker**: `docker-compose.yml` (разработка) и `docker-compose.prod.yml` (прод-подобный)

## Быстрый старт (Docker)

Требуется только Docker с плагином Compose v2 (`docker compose version`).

```bash
# из корня проекта (рядом лежат backend/ и frontend/)
docker compose up --build
```

Готово:

| Сервис | Адрес |
| --- | --- |
| Frontend (Vite dev server) | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger / OpenAPI | http://localhost:8000/docs |
| Health-check | http://localhost:8000/health |
| PostgreSQL | localhost:5432 (budget / budget) |
| Redis | localhost:6379 |

Что происходит при первом запуске:

1. собираются образы `backend/` (Python + зависимости из `poetry.lock`) и `frontend/` (Node + `npm ci`);
2. поднимается PostgreSQL и Redis (с healthcheck-ами);
3. backend ждёт готовности БД, контейнер применяет `alembic upgrade head` и стартует `uvicorn --reload`;
4. миграции создают схему и заполняют справочник валют (USD, EUR, RUB и др.), без них нельзя создать счёт;
5. frontend стартует с Vite и проксирует `/api` на `http://backend:8000` внутри docker-сети.

Исходники примонтированы томами, поэтому правки в `backend/` и `frontend/` подхватываются без пересборки.

### Демо-данные

Пустая база выглядит как сломанный интерфейс: нет счетов, категорий и записей.
Один скрипт создаёт готовый набор — проверенного пользователя, 6 счетов,
25 категорий, 4 метки, 387 записей за полгода, шаблоны и правила:

```bash
cd backend
python -m scripts.seed_demo            # создать (повторный запуск обновит данные)
python -m scripts.seed_demo --reset    # удалить данные пользователя и засеять заново
```

Логин и пароль по умолчанию печатает сам скрипт; их можно переопределить
переменными `DEMO_USER_EMAIL` и `DEMO_USER_PASSWORD`. В dev-сборке фронтенд
показывает эти данные прямо под формой входа (см. `frontend/src/__shared__/constants/demo.ts`).

Пользователь сразу `is_verified`, иначе вход запрещён: обычная регистрация требует
подтверждения почты, а для неё нужны Redis и настроенный отправитель писем.

### Полезные команды

```bash
docker compose ps                 # состояние сервисов
docker compose logs -f backend    # логи backend
docker compose logs -f frontend   # логи frontend
docker compose down               # остановить
docker compose down -v            # остановить и удалить данные БД
docker compose up --build backend # пересобрать только backend
```

### Тесты внутри docker

```bash
docker compose exec backend python -m pytest tests -q
```

### Фоновые задачи (RabbitMQ + Celery)

В проекте пока нет задач, поэтому брокер и воркер вынесены в профиль `workers`:

```bash
docker compose --profile workers up --build
```

RabbitMQ Management: http://localhost:15672 (guest / guest).

### Прод-подобный запуск

```bash
cp .env.example .env      # задайте SECRET_KEY и POSTGRES_PASSWORD
docker compose -f docker-compose.prod.yml up --build -d
```

Отличия от dev-файла:

- фронтенд собирается (`npm run build`) и раздаётся nginx, `/api` проксируется в backend (см. `frontend/nginx.conf`);
- backend запускается без autoreload, в 4 воркера uvicorn;
- исходники не монтируются, порты PostgreSQL и Redis не публикуются наружу;
- адрес приложения: http://localhost:5173.

Для `ENVIRONMENT=PROD` кука аутентификации выставляется с флагом `secure`, поэтому нужен HTTPS.
Для локального запуска по HTTP оставляйте `ENVIRONMENT=LOCAL`.

### Переменные окружения

Все параметры заданы в `docker-compose.yml` через значения по умолчанию, поэтому файл `.env`
не обязателен. Чтобы переопределить их, скопируйте шаблон:

```bash
cp .env.example .env
```

| Переменная | Назначение | По умолчанию |
| --- | --- | --- |
| `SECRET_KEY` | подпись JWT | `local-insecure-secret-key` |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | доступ к БД | `budgettracker` / `budget` / `budget` |
| `POSTGRES_HOST_PORT`, `BACKEND_HOST_PORT`, `FRONTEND_HOST_PORT` | публикуемые порты | 5432, 8000, 5173 |
| `ENVIRONMENT` | `LOCAL` \| `DEV` \| `TEST` \| `PROD` | `LOCAL` |
| `CORS_ORIGINS` | список origin-ов фронтенда (JSON) | `["http://localhost:5173","http://127.0.0.1:5173"]` |
| `RUN_MIGRATIONS` | применять миграции при старте backend | `true` |
| `VITE_API_PROXY_TARGET` | куда Vite проксирует `/api` | `http://backend:8000` |

## Локальная разработка без Docker

### Backend

```bash
cd backend
poetry install                       # или python -m venv .venv && pip install ...
cp .env.example .env                 # POSTGRES_HOST=localhost и т.п.
alembic upgrade head                 # применить миграции
uvicorn src.main:app --reload
```

Нужны локальные PostgreSQL (`POSTGRES_*` в `.env`) и Redis (`REDIS_*`).

### Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
npm run build          # сборка в dist/
```

Vite проксирует `/api` на `http://localhost:8000`; адрес меняется переменной
`VITE_API_PROXY_TARGET` (см. `frontend/vite.config.ts`).

### Тесты

```bash
cd backend
POSTGRES_HOST=127.0.0.1 TEST_POSTGRES_HOST=127.0.0.1 python -m pytest tests -q
```

Тесты создают и удаляют собственные БД, поэтому нужен доступ к серверу PostgreSQL.

## Как фронтенд работает с API

Всё, что видно на экранах, приходит с backend — мок-данные остались только на
витрине компонентов `/design`. Слой доступа разложен по трём уровням:

```
src/api/types.ts     — DTO как в OpenAPI (snake_case, ничего не выдумываем)
src/api/*.ts         — по модулю на домен: auth, users, accounts, categories,
                       transactions, currencies, analytics, tags, templates,
                       rules, billing
src/api/mappers.ts   — DTO → модель интерфейса (camelCase, знак суммы, подписи осей)
src/store/*.ts       — zustand: сессия, справочники, список записей
```

- **Сессия.** JWT лежит в httpOnly-куке `access_token`, поэтому «вошёл или нет»
  определяется запросом `GET /api/users/me` при старте (`src/app/SessionGate.tsx`).
  Любой 401 сбрасывает состояние и уводит на `/login` с запоминанием адреса.
- **Запросы.** `fetch` с `credentials: 'include'`; на 401 клиент зовёт обработчик,
  на ошибки FastAPI разбирает `{detail}` (в том числе массив ошибок валидации).
- **Фильтры записей** уходят на сервер целиком: `q`, `account_ids`, `category_ids`,
  `tag_ids`, `currency_ids`, `types`, `amount_min`, `amount_max`, `sort`.
  Количество найденного берётся из заголовка `X-Total-Count`.
- **Справочники** (счета, дерево категорий, метки, шаблоны, правила, курсы)
  загружаются один раз после входа в `src/store/finance.ts`.
- **Прокси.** Vite отправляет `/api` на backend (`VITE_API_PROXY_TARGET`,
  по умолчанию `http://localhost:8000`), поэтому CORS и SameSite-куки
  в разработке не мешают.

Проверить связку без браузера можно тремя способами:

```bash
bash tools/smoke-api.sh                            # читающие эндпоинты всех экранов
python3 tools/smoke_write.py                       # запись: запись, метка, шаблон,
                                                   # правило, способ оплаты, профиль
cd frontend && node tools/render-check.mts         # разметка экранных состояний
```

`render-check.mts` рендерит на сервере те же компоненты, что уходят в браузер
(плашку ошибки запроса, форму входа, защиту закрытого маршрута), поэтому ловит
поломки разметки и переводов без Playwright.

## Ограничения текущей версии

- **Переводы между счетами** пока не парные: `type=transfer` списывает сумму с
  одного счёта и не создаёт приход на втором, поэтому в форме записи режим
  перевода отключён.
- **Синхронизация с банком** не подключена: поля `is_locked` у счёта и импорта
  выписок нет, счета ведутся вручную.
- **Оплата** идёт через провайдера из `BILLING_PROVIDER`; в локальной среде это
  `mock`, который сразу подтверждает платёж. Провайдер без настроек отвечает 503,
  а платёж помечается `failed` — тихого отката на mock нет.
- **Подтверждение почты** требует Redis и отправителя писем; для локальной
  работы используйте `scripts/seed_demo.py`.

## Миграции

```bash
cd backend
alembic upgrade head                                  # применить
alembic downgrade -1                                  # откатить одну
alembic revision --autogenerate -m "add field"        # новая миграция
```

История лежит в `backend/src/migrations/versions/`:

- `..._initial_schema.py` — схема (users, currencies, accounts, categories, transactions, subscriptions);
- `7c1f0a9b2d34_seed_base_currencies.py` — базовый справочник валют.

## API

Все финансовые эндпоинты требуют аутентификации (кука с JWT) и изолированы по владельцу:

| Метод | Путь | Назначение |
| --- | --- | --- |
| POST | `/api/auth/register`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/refresh` | аутентификация |
| GET/PATCH | `/api/users/me` | профиль, `GET .../export`, `DELETE .../me` |
| CRUD | `/api/finance/accounts` | счета, `GET .../balance`, `GET .../{id}/summary` |
| CRUD | `/api/finance/categories` | категории, `GET .../tree`, `GET .../stats` |
| CRUD | `/api/finance/transactions` | записи, `.../summary`, `.../export`, `.../bulk-delete` |
| CRUD | `/api/finance/tags`, `.../templates`, `.../rules` | метки, шаблоны, правила авто-категоризации |
| PUT/DELETE | `/api/finance/currencies/{code}/rate` | личный курс валюты пользователя |
| GET | `/api/finance/currencies` | справочник валют (публично); изменение — только суперпользователь |
| GET | `/api/analytics/{summary,timeseries,by-category,by-account,matrix}` | аналитика (отдельное приложение) |
| GET/POST/DELETE | `/api/billing/{plans,providers,subscription,payment-methods,payments}` | тарифы и оплата |

Полное описание: http://localhost:8000/docs, подробности по контракту — `backend/docs/API.md`.

## Структура проекта

```
BudgetTracker/
├── docker-compose.yml          # dev-стек: postgres, redis, backend, frontend (+ workers)
├── docker-compose.prod.yml     # прод-подобный стек: nginx + собранный frontend
├── .env.example                # шаблон переменных для compose
├── backend/
│   ├── Dockerfile              # python:3.13-slim + poetry install --only main
│   ├── entrypoint.sh           # alembic upgrade head + запуск команды
│   ├── alembic.ini
│   ├── poetry.lock / pyproject.toml
│   ├── src/
│   │   ├── main.py             # сборка приложения, CORS, /health
│   │   ├── config.py           # настройки из окружения
│   │   ├── database.py         # движок и сессии
│   │   ├── dao.py / service.py / viewset.py / permissions.py   # общий каркас слоёв
│   │   ├── users/              # домен пользователей (эталон архитектуры)
│   │   ├── finance/            # счета, категории, записи, метки, шаблоны, правила
│   │   ├── analytics/          # отдельное приложение аналитики (§8)
│   │   ├── billing/            # тарифы, подписка, платежи, провайдеры
│   │   ├── notifications/      # отправка уведомлений (email/telegram, заглушки)
│   │   └── migrations/         # alembic env.py и версии миграций
│   ├── scripts/seed_demo.py    # демо-данные для локальной разработки
│   ├── docs/API.md             # контракт API и решения по эндпоинтам
│   └── tests/                  # pytest: users/, finance/, analytics/, billing/
└── frontend/
    ├── Dockerfile              # стадии: deps -> development / build -> production (nginx)
    ├── nginx.conf              # SPA + проксирование /api
    ├── vite.config.ts          # алиасы, dev-прокси, порт
    └── src/
        ├── app/                # точка входа, роутинг, проверка сессии
        ├── api/                # DTO, модули эндпоинтов, мапперы
        ├── store/              # zustand: сессия, справочники, записи
        ├── __pages__/          # страницы
        ├── components/         # переиспользуемые UI-компоненты
        └── __shared__/         # общие типы, утилиты, демо-константы
```

## Возможности

- несколько счетов разных типов (наличные, карта, накопительный, кредитный, инвестиции);
- иерархия категорий с контролем типа родителя;
- транзакции с автоматическим пересчётом баланса счёта и конвертацией по курсу;
- подписки и регулярные платежи с расчётом следующей даты;
- сводная аналитика по категориям и балансу в базовой валюте;
- мультивалютность на основе справочника курсов.

## Решение проблем

| Симптом | Решение |
| --- | --- |
| `port is already allocated` | занят 5432/8000/5173 — задайте `POSTGRES_HOST_PORT`, `BACKEND_HOST_PORT`, `FRONTEND_HOST_PORT` в `.env` |
| backend перезапускается | `docker compose logs backend`: обычно БД ещё не готова или неверный пароль PostgreSQL |
| схема БД устарела | `docker compose exec backend alembic upgrade head` или `docker compose down -v` для чистой БД |
| фронтенд не видит API | проверьте `VITE_API_PROXY_TARGET` и что backend healthy: `docker compose ps` |
| изменили `frontend/package.json` | `docker compose build --no-cache frontend` (зависимости ставятся в образ) |
