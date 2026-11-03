"""Модели биллинга: тарифы, подписки, способы оплаты и платежи."""

import uuid
from datetime import datetime
from enum import Enum
from typing import List
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base
from ..users.models import UserModel


def _enum_values(enum_cls) -> List[str]:
    """Stores enum members by their value instead of their name."""
    return [member.value for member in enum_cls]


class PlanPeriod(str, Enum):
    """За какой срок списывается цена тарифа."""

    NONE = "none"
    MONTH = "month"
    YEAR = "year"


class SubscriptionStatus(str, Enum):
    """Состояние подписки на тариф."""

    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"


class PaymentStatus(str, Enum):
    """Состояние платежа."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentKind(str, Enum):
    """За что платёж."""

    SUBSCRIPTION = "subscription"
    METHOD_ATTACH = "method_attach"


class PaymentMethodKind(str, Enum):
    """Чем платит пользователь."""

    CARD = "card"
    CRYPTO = "crypto"
    BANK_TRANSFER = "bank_transfer"


class PlanModel(Base):
    """Тариф: цена, период списания и список возможностей."""

    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(sa.String(32), primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    price: Mapped[float] = mapped_column(sa.Float, default=0.0, nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(3), default="USD", nullable=False)
    period: Mapped[PlanPeriod] = mapped_column(
        sa.Enum(PlanPeriod, name="plan_period", values_callable=_enum_values),
        default=PlanPeriod.NONE,
        nullable=False,
    )
    #: Список возможностей тарифа в человекочитаемом виде (JSON-массив строк)
    features: Mapped[list] = mapped_column(sa.JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    #: Порядок вывода на экране «Тарифы»
    sort_order: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=func.now(), nullable=True)

    subscriptions: Mapped[List["PlanSubscriptionModel"]] = relationship("PlanSubscriptionModel", back_populates="plan")


class PlanSubscriptionModel(Base):
    """Подписка пользователя на тариф."""

    __tablename__ = "plan_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    plan_code: Mapped[str] = mapped_column(sa.String(32), sa.ForeignKey("plans.code"), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        sa.Enum(SubscriptionStatus, name="subscription_status", values_callable=_enum_values),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now(), nullable=False)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True)
    #: Пользователь отменил продление, но период ещё не закончился
    cancel_at_period_end: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    #: Как оплачено: код провайдера (mock, stripe, crypto)
    provider: Mapped[str] = mapped_column(sa.String(32), default="mock", nullable=False)
    provider_reference: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=func.now(), nullable=True)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="plan_subscriptions")
    plan: Mapped["PlanModel"] = relationship("PlanModel", back_populates="subscriptions", lazy="joined")


class PaymentMethodModel(Base):
    """Сохранённый способ оплаты: карта, крипто-кошелёк или банковский перевод."""

    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    provider: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    kind: Mapped[PaymentMethodKind] = mapped_column(
        sa.Enum(PaymentMethodKind, name="payment_method_kind", values_callable=_enum_values),
        default=PaymentMethodKind.CARD,
        nullable=False,
    )
    brand: Mapped[Optional[str]] = mapped_column(sa.String(32), nullable=True)
    last4: Mapped[Optional[str]] = mapped_column(sa.String(4), nullable=True)
    is_default: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    #: Идентификатор способа оплаты на стороне провайдера
    provider_reference: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="payment_methods")


class PaymentModel(Base):
    """Платёж (счёт): создаётся до подтверждения провайдером."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    subscription_id: Mapped[Optional[int]] = mapped_column(
        sa.Integer,
        sa.ForeignKey("plan_subscriptions.id", ondelete="SET NULL"),
        nullable=True,
    )
    plan_code: Mapped[Optional[str]] = mapped_column(sa.String(32), nullable=True)
    kind: Mapped[PaymentKind] = mapped_column(
        sa.Enum(PaymentKind, name="payment_kind", values_callable=_enum_values),
        default=PaymentKind.SUBSCRIPTION,
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(sa.Float, nullable=False)
    currency: Mapped[str] = mapped_column(sa.String(3), default="USD", nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        sa.Enum(PaymentStatus, name="payment_status", values_callable=_enum_values),
        default=PaymentStatus.PENDING,
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    #: Идентификатор платежа у провайдера — по нему приходит вебхук
    provider_reference: Mapped[Optional[str]] = mapped_column(sa.String(255), index=True, nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=func.now(), nullable=True)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="payments")
