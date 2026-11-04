import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .admin import admin_router
from .analytics import analytics_router
from .billing import billing_router
from .config import settings
from .finance import accounts_router
from .finance import categories_router
from .finance import currencies_router
from .finance import rules_router
from .finance import subscriptions_router
from .finance import tags_router
from .finance import templates_router
from .finance import transactions_router
from .users import auth_router
from .users import users_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Подключает Redis на старте и отдаёт его сервисам.

    Redis нужен для токенов подтверждения почты и кеша. В локальной среде его
    может не быть: тогда приложение поднимается без кэша и пишет предупреждение,
    а не падает на старте.
    """
    from .cache import Cache
    from .config import settings
    from .users.service import UserService

    client = None
    try:
        client = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        await client.ping()
        await UserService.initialize_redis(client)
        Cache.configure(client)
        logger.info("Redis connected: %s:%s", settings.REDIS_HOST, settings.REDIS_PORT)
    except Exception as caught:  # noqa: BLE001 — старт не должен падать без кэша
        if settings.ENVIRONMENT != "LOCAL":
            raise
        logger.warning("Redis is unavailable (%s): running without cache", caught)
        if client is not None:
            try:
                await client.aclose()
            except Exception:  # noqa: BLE001
                pass
        client = None

    try:
        yield
    finally:
        Cache.reset()
        if client is not None:
            try:
                await client.aclose()
            except Exception:  # noqa: BLE001
                pass


app = FastAPI(title="BudgetTracker API", version="0.1.0", lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)


@app.get("/health", tags=["service"], summary="Проверка живости сервиса")
async def health_check() -> dict:
    """Используется docker HEALTHCHECK и балансировщиками нагрузки."""
    return {"status": "ok", "environment": settings.ENVIRONMENT}


# Include routers
app.include_router(admin_router)
app.include_router(accounts_router)
app.include_router(analytics_router)
app.include_router(billing_router)
app.include_router(categories_router)
app.include_router(transactions_router)
app.include_router(subscriptions_router)
app.include_router(currencies_router)
app.include_router(tags_router)
app.include_router(templates_router)
app.include_router(rules_router)
app.include_router(auth_router)
app.include_router(users_router)
