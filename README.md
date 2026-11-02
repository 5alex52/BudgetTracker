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
| GET/PATCH | `/api/users/me` | профиль |
| CRUD | `/api/finance/accounts` | счета, `GET /api/finance/accounts/balance` — сводный баланс |
| CRUD | `/api/finance/categories` | категории и подкатегории |
| CRUD | `/api/finance/transactions` | транзакции, `GET /api/finance/transactions/summary` — аналитика |
| CRUD | `/api/finance/subscriptions` | подписки, `GET .../upcoming`, `POST .../{id}/advance` |
| GET | `/api/finance/currencies` | справочник валют (публично); изменение — только суперпользователь |

Полное описание: http://localhost:8000/docs.

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
│   │   ├── finance/            # финансовый домен
│   │   ├── notifications/      # отправка уведомлений (email/telegram, заглушки)
│   │   └── migrations/         # alembic env.py и версии миграций
│   └── tests/                  # pytest: users/, finance/
└── frontend/
    ├── Dockerfile              # стадии: deps -> development / build -> production (nginx)
    ├── nginx.conf              # SPA + проксирование /api
    ├── vite.config.ts          # алиасы, dev-прокси, порт
    └── src/
        ├── app/                # точка входа, роутинг
        ├── __pages__/          # страницы
        ├── __widgets__/        # переиспользуемые UI-компоненты
        └── __shared__/         # типы и утилиты
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
