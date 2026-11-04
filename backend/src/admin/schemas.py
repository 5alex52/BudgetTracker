"""Схемы админ-панели: пользователи и статистика подписок."""

import uuid
from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field

from ..billing.models import SubscriptionStatus


class AdminUser(BaseModel):
    """Пользователь в списке админки вместе с его текущей подпиской."""

    id: uuid.UUID
    fullname: str
    email: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    plan_code: str
    plan_name: str
    subscription_status: SubscriptionStatus
    current_period_end: Optional[datetime] = None
    is_premium: bool


class AdminUserPage(BaseModel):
    items: List[AdminUser]
    total: int
    offset: int
    limit: int


class AdminUserUpdate(BaseModel):
    """Что админ может изменить в чужом аккаунте."""

    firstname: Optional[str] = Field(None, max_length=255)
    lastname: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class AdminPlanStat(BaseModel):
    code: str
    name: str
    count: int


class AdminStats(BaseModel):
    users_total: int
    users_new_30d: int
    premium_total: int
    free_total: int
    expiring_soon: int
    revenue_30d: float
    plans: List[AdminPlanStat] = Field(default_factory=list)


class AdminSubscriptionPoint(BaseModel):
    """Подписки на конкретную дату."""

    date: str
    premium: int
    free: int


class AdminSubscriptionTimeline(BaseModel):
    """История изменения количества подписок за последние 30 дней."""

    points: List[AdminSubscriptionPoint] = Field(default_factory=list)


class AdminGrantRequest(BaseModel):
    """Выдача подписки без оплаты."""

    plan_code: str = Field(..., min_length=1, max_length=32)
