"""HTTP-слой админ-панели. Доступ — только суперпользователям."""

import uuid
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import status
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.database import get_async_session_maker
from src.users.dependencies import get_current_superuser

from .schemas import AdminGrantRequest
from .schemas import AdminStats
from .schemas import AdminSubscriptionTimeline
from .schemas import AdminUser
from .schemas import AdminUserPage
from .schemas import AdminUserUpdate
from .service import AdminService

admin_router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_superuser)],
)


@admin_router.get("/stats", status_code=status.HTTP_200_OK, response_model=AdminStats)
async def get_stats(
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AdminStats:
    """Сводка по пользователям и подпискам."""
    return await AdminService.get_stats(session_maker=session_maker)


@admin_router.get(
    "/stats/subscriptions",
    status_code=status.HTTP_200_OK,
    response_model=AdminSubscriptionTimeline,
)
async def get_subscription_timeline(
    days: int = Query(30, ge=7, le=365),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AdminSubscriptionTimeline:
    """График изменения количества подписок за последние N дней."""
    return await AdminService.get_subscription_timeline(days=days, session_maker=session_maker)


@admin_router.get("/users", status_code=status.HTTP_200_OK, response_model=AdminUserPage)
async def list_users(
    search: Optional[str] = Query(None, max_length=255),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AdminUserPage:
    """Список пользователей с поиском по имени и почте."""
    return await AdminService.list_users(
        search=search,
        offset=offset,
        limit=limit,
        session_maker=session_maker,
    )


@admin_router.patch("/users/{user_id}", status_code=status.HTTP_200_OK, response_model=AdminUser)
async def update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdate,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AdminUser:
    """Блокировка и подтверждение почты."""
    return await AdminService.update_user(
        user_id=user_id,
        payload=payload,
        session_maker=session_maker,
    )


@admin_router.post(
    "/users/{user_id}/subscription",
    status_code=status.HTTP_200_OK,
    response_model=AdminUser,
)
async def grant_subscription(
    user_id: uuid.UUID,
    payload: AdminGrantRequest,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AdminUser:
    """Выдать подписку бесплатно на срок тарифа."""
    return await AdminService.grant_subscription(
        user_id=user_id,
        request=payload,
        session_maker=session_maker,
    )


@admin_router.delete(
    "/users/{user_id}/subscription",
    status_code=status.HTTP_200_OK,
    response_model=AdminUser,
)
async def revoke_subscription(
    user_id: uuid.UUID,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AdminUser:
    """Отозвать подписку сразу."""
    return await AdminService.revoke_subscription(
        user_id=user_id,
        session_maker=session_maker,
    )
