"""Admin panel service: user list, statistics and manual subscription management."""

import uuid
from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import Optional
from typing import Sequence

from fastapi import HTTPException
from fastapi import status
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..billing.models import PaymentModel
from ..billing.models import PaymentStatus
from ..billing.models import PlanModel
from ..billing.models import PlanPeriod
from ..billing.models import PlanSubscriptionModel
from ..billing.models import SubscriptionStatus
from ..billing.service import FREE_PLAN_CODE
from ..billing.service import _period_end
from ..database import async_session_maker as default_session_maker
from ..users.models import UserModel
from .schemas import AdminGrantRequest
from .schemas import AdminPlanStat
from .schemas import AdminStats
from .schemas import AdminSubscriptionPoint
from .schemas import AdminSubscriptionTimeline
from .schemas import AdminUser
from .schemas import AdminUserPage
from .schemas import AdminUserUpdate


def _not_found(detail: str = "User not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _paid_and_active(subscription: PlanSubscriptionModel, now: datetime) -> bool:
    """Paid subscription is active right now — same logic as in entitlements."""
    if subscription.plan_code == FREE_PLAN_CODE or subscription.status != SubscriptionStatus.ACTIVE:
        return False
    until = subscription.current_period_end
    return until is None or until > now


class AdminService:
    @classmethod
    async def _latest_subscriptions(
        cls,
        session: AsyncSession,
        user_ids: Optional[Sequence[uuid.UUID]] = None,
    ) -> Dict[uuid.UUID, PlanSubscriptionModel]:
        """Latest subscription for each user in a single query."""
        latest_ids = select(func.max(PlanSubscriptionModel.id)).group_by(PlanSubscriptionModel.user_id)
        if user_ids is not None:
            if not user_ids:
                return {}
            latest_ids = latest_ids.where(PlanSubscriptionModel.user_id.in_(user_ids))

        stmt = (
            select(PlanSubscriptionModel)
            .options(selectinload(PlanSubscriptionModel.plan))
            .where(PlanSubscriptionModel.id.in_(latest_ids))
        )
        rows = (await session.execute(stmt)).scalars().all()
        return {row.user_id: row for row in rows}

    @classmethod
    def _row(cls, user: UserModel, subscription: Optional[PlanSubscriptionModel], now: datetime) -> AdminUser:
        if subscription is None:
            return AdminUser(
                id=user.id,
                fullname=user.fullname,
                email=user.email,
                is_active=user.is_active,
                is_verified=user.is_verified,
                is_superuser=user.is_superuser,
                created_at=user.created_at,
                last_login_at=user.last_login_at,
                plan_code=FREE_PLAN_CODE,
                plan_name="Free",
                subscription_status=SubscriptionStatus.ACTIVE,
                current_period_end=None,
                is_premium=False,
            )

        return AdminUser(
            id=user.id,
            fullname=user.fullname,
            email=user.email,
            is_active=user.is_active,
            is_verified=user.is_verified,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            plan_code=subscription.plan_code,
            plan_name=subscription.plan.name if subscription.plan else subscription.plan_code,
            subscription_status=subscription.status,
            current_period_end=subscription.current_period_end,
            is_premium=_paid_and_active(subscription, now),
        )

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
            total = await session.scalar(select(func.count()).select_from(UserModel).where(*conditions))
            stmt = (
                select(UserModel)
                .where(*conditions)
                .order_by(UserModel.created_at.desc(), UserModel.email)
                .offset(offset)
                .limit(limit)
            )
            users = list((await session.execute(stmt)).scalars().all())
            subscriptions = await cls._latest_subscriptions(session, [user.id for user in users])

        now = datetime.now()
        return AdminUserPage(
            items=[cls._row(user, subscriptions.get(user.id), now) for user in users],
            total=int(total or 0),
            offset=offset,
            limit=limit,
        )

    @classmethod
    async def _read_user(
        cls, session: AsyncSession, user_id: uuid.UUID
    ) -> tuple[UserModel, Optional[PlanSubscriptionModel]]:
        user = await session.get(UserModel, user_id)
        if user is None:
            raise _not_found()
        subscriptions = await cls._latest_subscriptions(session, [user_id])
        return user, subscriptions.get(user_id)

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
            user = await session.get(UserModel, user_id)
            if user is None:
                raise _not_found()

            # Admin must not block themselves or another admin and lose access
            if changes.get("is_active") is False and user.is_superuser:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot block a superuser",
                )

            # Check email uniqueness if it's being changed
            if "email" in changes and changes["email"] != user.email:
                existing = await session.scalar(
                    select(UserModel).where(UserModel.email == changes["email"], UserModel.id != user_id)
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
            user, subscription = await cls._read_user(session, user_id)
            result = cls._row(user, subscription, datetime.now())

        return result

    # ------------------------------------------------------------------ #
    #  Subscriptions
    # ------------------------------------------------------------------ #

    @classmethod
    async def grant_subscription(
        cls,
        user_id: uuid.UUID,
        request: AdminGrantRequest,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> AdminUser:
        """Grants a paid plan without payment: provider is `admin`, duration is the plan period."""
        maker = cls._maker(session_maker)

        async with maker() as session:
            user = await session.get(UserModel, user_id)
            if user is None:
                raise _not_found()

            plan = await session.get(PlanModel, request.plan_code)
            if plan is None or not plan.is_active:
                raise _not_found("Plan not found")
            if plan.period == PlanPeriod.NONE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Choose a paid plan",
                )

            now = datetime.now()
            # Close previous active subscriptions so there is exactly one "current" subscription
            await session.execute(
                update(PlanSubscriptionModel)
                .where(
                    PlanSubscriptionModel.user_id == user_id,
                    PlanSubscriptionModel.status == SubscriptionStatus.ACTIVE,
                )
                .values(status=SubscriptionStatus.CANCELED, cancel_at_period_end=False)
            )
            session.add(
                PlanSubscriptionModel(
                    user_id=user_id,
                    plan_code=plan.code,
                    status=SubscriptionStatus.ACTIVE,
                    started_at=now,
                    current_period_end=_period_end(plan, now),
                    provider="admin",
                )
            )
            await session.commit()
            await session.refresh(user)
            user, subscription = await cls._read_user(session, user_id)
            result = cls._row(user, subscription, datetime.now())

        return result

    @classmethod
    async def revoke_subscription(
        cls,
        user_id: uuid.UUID,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> AdminUser:
        """Revokes a subscription immediately: the next rights check will return the free plan."""
        maker = cls._maker(session_maker)

        async with maker() as session:
            user = await session.get(UserModel, user_id)
            if user is None:
                raise _not_found()

            result = await session.execute(
                update(PlanSubscriptionModel)
                .where(
                    PlanSubscriptionModel.user_id == user_id,
                    PlanSubscriptionModel.status == SubscriptionStatus.ACTIVE,
                )
                .values(status=SubscriptionStatus.CANCELED, cancel_at_period_end=False)
            )
            if not result.rowcount:
                raise _not_found("Active subscription not found")
            await session.commit()
            await session.refresh(user)
            user, subscription = await cls._read_user(session, user_id)
            row = cls._row(user, subscription, datetime.now())

        return row

    # ------------------------------------------------------------------ #
    #  Statistics
    # ------------------------------------------------------------------ #

    @classmethod
    async def get_stats(cls, session_maker: Optional[async_sessionmaker] = None) -> AdminStats:
        maker = cls._maker(session_maker)
        now = datetime.now()

        async with maker() as session:
            users_total = int(await session.scalar(select(func.count()).select_from(UserModel)) or 0)
            users_new = int(
                await session.scalar(
                    select(func.count()).select_from(UserModel).where(UserModel.created_at >= now - timedelta(days=30))
                )
                or 0
            )
            subscriptions = list((await cls._latest_subscriptions(session)).values())
            revenue = float(
                await session.scalar(
                    select(func.coalesce(func.sum(PaymentModel.amount), 0.0)).where(
                        PaymentModel.status == PaymentStatus.SUCCEEDED,
                        PaymentModel.created_at >= now - timedelta(days=30),
                    )
                )
                or 0.0
            )
            plans = list((await session.execute(select(PlanModel).order_by(PlanModel.sort_order))).scalars().all())

        active = [subscription for subscription in subscriptions if _paid_and_active(subscription, now)]
        counts: Dict[str, int] = {}
        for subscription in active:
            counts[subscription.plan_code] = counts.get(subscription.plan_code, 0) + 1

        soon = now + timedelta(days=7)
        expiring = sum(
            1
            for subscription in active
            if subscription.current_period_end is not None and subscription.current_period_end <= soon
        )
        premium_total = len(active)

        return AdminStats(
            users_total=users_total,
            users_new_30d=users_new,
            premium_total=premium_total,
            free_total=users_total - premium_total,
            expiring_soon=expiring,
            revenue_30d=revenue,
            plans=[
                AdminPlanStat(
                    code=plan.code,
                    name=plan.name,
                    count=users_total - premium_total if plan.code == FREE_PLAN_CODE else counts.get(plan.code, 0),
                )
                for plan in plans
            ],
        )

    # ------------------------------------------------------------------ #
    #  Subscription timeline chart
    # ------------------------------------------------------------------ #

    @classmethod
    async def get_subscription_timeline(
        cls, days: int = 30, session_maker: Optional[async_sessionmaker] = None
    ) -> AdminSubscriptionTimeline:
        """Counts the number of paid/free users at the end of each day."""
        maker = cls._maker(session_maker)
        now = datetime.now()
        today = now.date()

        async with maker() as session:
            users_total = int(await session.scalar(select(func.count()).select_from(UserModel)) or 0)

            # All subscriptions to reconstruct history
            stmt = (
                select(PlanSubscriptionModel)
                .options(selectinload(PlanSubscriptionModel.plan))
                .order_by(PlanSubscriptionModel.started_at)
            )
            all_subs = list((await session.execute(stmt)).scalars().all())

        points: List[AdminSubscriptionPoint] = []
        for day_offset in range(days - 1, -1, -1):
            day = today - timedelta(days=day_offset)
            day_end = datetime.combine(day, datetime.max.time())

            # Count paid active subscriptions at end of day
            premium = 0
            for sub in all_subs:
                if sub.started_at > day_end:
                    continue
                if (
                    sub.status == SubscriptionStatus.CANCELED
                    and sub.current_period_end
                    and sub.current_period_end <= day_end
                ):
                    continue
                if sub.plan_code != FREE_PLAN_CODE and _paid_and_active(sub, day_end):
                    premium += 1

            points.append(
                AdminSubscriptionPoint(
                    date=day.isoformat(),
                    premium=premium,
                    free=users_total - premium,
                )
            )

        return AdminSubscriptionTimeline(points=points)
