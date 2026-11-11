import asyncio
import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .admin import admin_router
from .analytics import analytics_router
from .config import settings
from .finance import accounts_router
from .finance import categories_router
from .finance import currencies_router
from .finance import rules_router
from .finance import subscriptions_router
from .finance import tags_router
from .finance import service_subs_router
from .finance import templates_router
from .finance import transactions_router
from .users import auth_router
from .users import users_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Connects Redis at startup and provides it to services.

    Redis is used for email confirmation tokens and caching. In a local environment it may be
    unavailable: the application starts without cache and logs a warning instead of crashing.
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
    except Exception as caught:  # noqa: BLE001 — startup should not fail without cache
        if settings.ENVIRONMENT != "LOCAL":
            raise
        logger.warning("Redis is unavailable (%s): running without cache", caught)
        if client is not None:
            try:
                await client.aclose()
            except Exception:  # noqa: BLE001
                pass
        client = None

    # Background worker: executes the subscriptions' automatic billing rules on
    # a schedule so records appear without anyone opening the page. Disabled in
    # tests, where billing is driven explicitly.
    rule_task = None
    if settings.ENVIRONMENT != "TEST":
        from .database import async_session_maker
        from .finance.service_subs import subscription_rule_loop

        rule_task = asyncio.create_task(subscription_rule_loop(async_session_maker))

    try:
        yield
    finally:
        if rule_task is not None:
            rule_task.cancel()
            try:
                await rule_task
            except asyncio.CancelledError:
                pass
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


@app.get("/health", tags=["service"], summary="Service liveness check")
async def health_check() -> dict:
    """Used by docker HEALTHCHECK and load balancers."""
    return {"status": "ok", "environment": settings.ENVIRONMENT}


# Include routers
app.include_router(admin_router)
app.include_router(accounts_router)
app.include_router(analytics_router)
app.include_router(categories_router)
app.include_router(transactions_router)
app.include_router(subscriptions_router)
app.include_router(currencies_router)
app.include_router(tags_router)
app.include_router(templates_router)
app.include_router(service_subs_router)
app.include_router(rules_router)
app.include_router(auth_router)
app.include_router(users_router)
