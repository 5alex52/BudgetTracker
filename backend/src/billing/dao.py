"""Доступ к данным биллинга."""

import uuid
from datetime import datetime
from typing import List
from typing import Optional

from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import PaymentMethodModel
from .models import PaymentModel
from .models import PaymentStatus
from .models import PlanModel
from .models import PlanSubscriptionModel
from .models import SubscriptionStatus


class PlanDAO:
    """Справочник тарифов."""

    model = PlanModel

    @classmethod
    async def find_all_active(cls, session: AsyncSession) -> List[PlanModel]:
        stmt = select(PlanModel).where(PlanModel.is_active.is_(True)).order_by(PlanModel.sort_order, PlanModel.price)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def find_by_code(cls, session: AsyncSession, code: str) -> Optional[PlanModel]:
        stmt = select(PlanModel).where(PlanModel.code == code)
        result = await session.execute(stmt)
        return result.scalars().one_or_none()


class SubscriptionDAO:
    """Подписки пользователей."""

    model = PlanSubscriptionModel

    @classmethod
    async def find_current(cls, session: AsyncSession, user_id: uuid.UUID) -> Optional[PlanSubscriptionModel]:
        """Последняя подписка пользователя — она и считается текущей."""
        stmt = (
            select(PlanSubscriptionModel)
            .where(PlanSubscriptionModel.user_id == user_id)
            .order_by(PlanSubscriptionModel.id.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalars().one_or_none()

    @classmethod
    async def find_active(cls, session: AsyncSession, user_id: uuid.UUID) -> Optional[PlanSubscriptionModel]:
        stmt = (
            select(PlanSubscriptionModel)
            .where(
                PlanSubscriptionModel.user_id == user_id,
                PlanSubscriptionModel.status == SubscriptionStatus.ACTIVE,
            )
            .order_by(PlanSubscriptionModel.id.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalars().one_or_none()


class PaymentMethodDAO:
    """Способы оплаты."""

    model = PaymentMethodModel

    @classmethod
    async def find_all_by_user(cls, session: AsyncSession, user_id: uuid.UUID) -> List[PaymentMethodModel]:
        stmt = (
            select(PaymentMethodModel)
            .where(PaymentMethodModel.user_id == user_id)
            .order_by(PaymentMethodModel.is_default.desc(), PaymentMethodModel.id)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def find_one_by_user(
        cls, session: AsyncSession, method_id: int, user_id: uuid.UUID
    ) -> Optional[PaymentMethodModel]:
        stmt = select(PaymentMethodModel).where(
            PaymentMethodModel.id == method_id, PaymentMethodModel.user_id == user_id
        )
        result = await session.execute(stmt)
        return result.scalars().one_or_none()

    @classmethod
    async def clear_defaults(cls, session: AsyncSession, user_id: uuid.UUID) -> None:
        await session.execute(
            update(PaymentMethodModel)
            .where(
                PaymentMethodModel.user_id == user_id,
                PaymentMethodModel.is_default.is_(True),
            )
            .values(is_default=False)
        )


class PaymentDAO:
    """Платежи."""

    model = PaymentModel

    @classmethod
    async def find_all_by_user(
        cls,
        session: AsyncSession,
        user_id: uuid.UUID,
        offset: int = 0,
        limit: int = 100,
    ) -> List[PaymentModel]:
        stmt = (
            select(PaymentModel)
            .where(PaymentModel.user_id == user_id)
            .order_by(PaymentModel.id.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def find_one_by_user(
        cls, session: AsyncSession, payment_id: int, user_id: uuid.UUID
    ) -> Optional[PaymentModel]:
        stmt = select(PaymentModel).where(PaymentModel.id == payment_id, PaymentModel.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalars().one_or_none()

    @classmethod
    async def find_by_reference(cls, session: AsyncSession, reference: str) -> Optional[PaymentModel]:
        """Платёж по идентификатору у провайдера — так его находит вебхук."""
        stmt = select(PaymentModel).where(PaymentModel.provider_reference == reference)
        result = await session.execute(stmt)
        return result.scalars().one_or_none()

    @classmethod
    async def mark(
        cls,
        session: AsyncSession,
        payment: PaymentModel,
        status: PaymentStatus,
        reason=None,
    ) -> None:
        await session.execute(
            update(PaymentModel)
            .where(PaymentModel.id == payment.id)
            .values(status=status, failure_reason=reason, updated_at=datetime.now())
        )
