import uuid
from datetime import datetime
from typing import List
from typing import Optional
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base

if TYPE_CHECKING:
    from src.finance.models import AccountModel
    from src.finance.models import CategoryModel


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, index=True, default=uuid.uuid4)
    firstname: Mapped[str] = mapped_column(sa.String(255))
    lastname: Mapped[str] = mapped_column(sa.String(255))
    email: Mapped[str] = mapped_column(sa.String(255), index=True, unique=True)
    password: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    #: Telegram не обязателен: вход возможен по email, поэтому поле nullable.
    #: unique остаётся — двух одинаковых Telegram-аккаунтов быть не должно.
    telegram_id: Mapped[Optional[int]] = mapped_column(sa.Integer, index=True, unique=True, nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=func.now(), nullable=True)
    last_login_at: Mapped[datetime] = mapped_column(sa.DateTime, nullable=True)
    timezone: Mapped[str] = mapped_column(sa.String, default="Europe/Minsk")
    #: Код валюты, в которой показываются итоги (ссылка на справочник currencies, без FK:
    #: справочник живёт в finance, а пользователь не должен зависеть от порядка его сидов)
    base_currency: Mapped[str] = mapped_column(sa.String(3), default="BYN", nullable=True)
    #: Язык интерфейса по умолчанию для новых устройств
    locale: Mapped[str] = mapped_column(sa.String(8), default="ru", nullable=True)
    #: Тема оформления: system | light | dark
    theme: Mapped[str] = mapped_column(sa.String(16), default="system", nullable=True)
    #: Базовый период отчётов: day | week | month — с него открываются «Обзор» и «Аналитика»
    default_period: Mapped[str] = mapped_column(sa.String(8), default="month", nullable=True)
    photo: Mapped[str] = mapped_column(sa.String, nullable=True)
    git_username: Mapped[str] = mapped_column(sa.String, nullable=True)
    accounts: Mapped[List["AccountModel"]] = relationship("AccountModel", back_populates="user")
    categories: Mapped[List["CategoryModel"]] = relationship("CategoryModel", back_populates="user")
    tags: Mapped[List["TagModel"]] = relationship("TagModel", back_populates="user", cascade="all, delete-orphan")
    templates: Mapped[List["TemplateModel"]] = relationship(
        "TemplateModel", back_populates="user", cascade="all, delete-orphan"
    )
    rules: Mapped[List["RuleModel"]] = relationship("RuleModel", back_populates="user", cascade="all, delete-orphan")
    plan_subscriptions: Mapped[List["PlanSubscriptionModel"]] = relationship(
        "PlanSubscriptionModel", back_populates="user", cascade="all, delete-orphan"
    )
    payment_methods: Mapped[List["PaymentMethodModel"]] = relationship(
        "PaymentMethodModel", back_populates="user", cascade="all, delete-orphan"
    )
    payments: Mapped[List["PaymentModel"]] = relationship(
        "PaymentModel", back_populates="user", cascade="all, delete-orphan"
    )
    fullname = sa.orm.column_property(firstname + " " + lastname)


class RefreshSessionModel(Base):
    __tablename__ = "refresh_session"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    refresh_token: Mapped[uuid.UUID] = mapped_column(UUID, index=True)
    expires_in: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, sa.ForeignKey("users.id", ondelete="CASCADE"))
    device_name: Mapped[str] = mapped_column(sa.String, nullable=True)
    device_type: Mapped[str] = mapped_column(sa.String, nullable=True)
    last_login: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=func.now(), default=func.now())
