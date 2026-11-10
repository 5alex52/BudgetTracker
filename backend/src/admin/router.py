"""Admin panel HTTP layer. Access restricted to superusers."""

import uuid
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import status
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.database import get_async_session_maker
from src.users.dependencies import get_current_superuser

from .schemas import AdminStats
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
    """Summary of registered users."""
    return await AdminService.get_stats(session_maker=session_maker)


@admin_router.get("/users", status_code=status.HTTP_200_OK, response_model=AdminUserPage)
async def list_users(
    search: Optional[str] = Query(None, max_length=255),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AdminUserPage:
    """List users with search by name and email."""
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
    """Block/unblock user and verify email."""
    return await AdminService.update_user(
        user_id=user_id,
        payload=payload,
        session_maker=session_maker,
    )
