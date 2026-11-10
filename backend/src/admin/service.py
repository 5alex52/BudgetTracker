"""Admin panel service: user list and statistics."""

import uuid
from datetime import datetime
from datetime import timedelta
from typing import Optional

from fastapi import HTTPException
from fastapi import status
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session_maker as default_session_maker
from ..users.models import UserModel
from .schemas import AdminStats
from .schemas import AdminUser
from .schemas import AdminUserPage
from .schemas import AdminUserUpdate


def _not_found(detail: str = "User not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class AdminService:
    @classmethod
    def _maker(cls, session_maker: Optional[async_sessionmaker]) -> async_sessionmaker:
        return session_maker or default_session_maker

    # ------------------------------------------------------------------ #
    #  Users
    # ------------------------------------------------------------------ #

    @classmethod
    async def list_users(
        cls,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 20,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> AdminUserPage:
        maker = cls._maker(session_maker)
        conditions = []
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            conditions.append(
                or_(
                    UserModel.email.ilike(pattern),
                    UserModel.firstname.ilike(pattern),
                    UserModel.lastname.ilike(pattern),
                )
            )

        async with maker() as session:
            total = await session.scalar(
                select(func.count()).select_from(UserModel).where(*conditions)
            )
            stmt = (
                select(UserModel)
                .where(*conditions)
                .order_by(UserModel.created_at.desc(), UserModel.email)
                .offset(offset)
                .limit(limit)
            )
            users = list((await session.execute(stmt)).scalars().all())

        return AdminUserPage(
            items=[
                AdminUser(
                    id=user.id,
                    fullname=user.fullname,
                    email=user.email,
                    is_active=user.is_active,
                    is_verified=user.is_verified,
                    is_superuser=user.is_superuser,
                    created_at=user.created_at,
                    last_login_at=user.last_login_at,
                )
                for user in users
            ],
            total=int(total or 0),
            offset=offset,
            limit=limit,
        )

    @classmethod
    async def _read_user(cls, session: AsyncSession, user_id: uuid.UUID) -> UserModel:
        user = await session.get(UserModel, user_id)
        if user is None:
            raise _not_found()
        return user

    @classmethod
    async def update_user(
        cls,
        user_id: uuid.UUID,
        payload: AdminUserUpdate,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> AdminUser:
        maker = cls._maker(session_maker)
        changes = payload.model_dump(exclude_unset=True)

        async with maker() as session:
            user = await cls._read_user(session, user_id)

            # Admin must not block themselves or another admin and lose access
            if changes.get("is_active") is False and user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot block a superuser",
                )

            # Check email uniqueness if it's being changed
            if "email" in changes and changes["email"] != user.email:
                existing = await session.scalar(
                    select(UserModel).where(
                        UserModel.email == changes["email"], UserModel.id != user_id
                    )
                )
                if existing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already in use",
                    )

            for field, value in changes.items():
                setattr(user, field, value)
            await session.commit()
            # Refresh the object after commit so fullname is recalculated
            await session.refresh(user)
            result = cls._user_row(user)

        return result

    @classmethod
    def _user_row(cls, user: UserModel) -> AdminUser:
        return AdminUser(
            id=user.id,
            fullname=user.fullname,
            email=user.email,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )

    # ------------------------------------------------------------------ #
    #  Statistics
    # ------------------------------------------------------------------ #

    @classmethod
    async def get_stats(
        cls, session_maker: Optional[async_sessionmaker] = None
    ) -> AdminStats:
        maker = cls._maker(session_maker)
        now = datetime.now()

        async with maker() as session:
            users_total = int(
                await session.scalar(select(func.count()).select_from(UserModel)) or 0
            )
            users_new = int(
                await session.scalar(
                    select(func.count())
                    .select_from(UserModel)
                    .where(UserModel.created_at >= now - timedelta(days=30))
                )
                or 0
            )

        return AdminStats(
            users_total=users_total,
            users_new_30d=users_new,
        )
