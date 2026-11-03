"""Схемы биллинга: тарифы, подписка, способы оплаты, платежи."""

from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from .models import PaymentKind
from .models import PaymentMethodKind
from .models import PaymentStatus
from .models import PlanPeriod
from .models import SubscriptionStatus


class PlanResponse(BaseModel):
    """Тариф для экрана «Тарифы и платежи»."""

    code: str
    name: str
    description: Optional[str] = None
    price: float
    currency: str
    period: PlanPeriod
    features: List[str] = Field(default_factory=list)
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class SubscriptionResponse(BaseModel):
    """Текущая подписка пользователя."""

    id: Optional[int] = None
    plan_code: str
    plan_name: str
    status: SubscriptionStatus
    started_at: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    provider: str = "mock"

    model_config = ConfigDict(from_attributes=True)


class Entitlements(BaseModel):
    """Что доступно пользователю по его тарифу.

    Единая точка правды для лимитов: и сервер (создание счетов, валют), и
    клиент (премиум-виджеты) читают один и тот же ответ, поэтому «подписка
    есть, а виджеты не появились» больше не повторится.
    """

    plan_code: str
    plan_name: str
    is_paid: bool = False
    is_active: bool = False
    #: ``None`` — без ограничения
    max_accounts: Optional[int] = None
    multi_currency: bool = False
    advanced_analytics: bool = False
    current_period_end: Optional[datetime] = None
    reason: Optional[str] = None


class SubscriptionChangeRequest(BaseModel):
    """Оформление или смена тарифа."""

    plan_code: str = Field(..., min_length=1, max_length=32)
    provider: Optional[str] = Field(None, description="Провайдер оплаты; по умолчанию из настроек")
    return_url: Optional[str] = Field(None, description="Куда вернуть пользователя после оплаты")


class CheckoutSession(BaseModel):
    """Сессия оплаты: ссылка на страницу провайдера и данные платежа."""

    payment_id: int
    status: PaymentStatus
    provider: str
    provider_reference: Optional[str] = None
    checkout_url: Optional[str] = None
    #: Мок-провайдер подтверждает платёж сразу — фронтенду не нужно никуда редиректить
    requires_redirect: bool = False
    subscription: Optional[SubscriptionResponse] = None


class PaymentMethodResponse(BaseModel):
    """Сохранённый способ оплаты."""

    id: int
    provider: str
    kind: PaymentMethodKind
    brand: Optional[str] = None
    last4: Optional[str] = None
    is_default: bool = False
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentMethodCreate(BaseModel):
    """Привязка способа оплаты.

    Данные карты сюда не попадают: номер и CVC вводятся на стороне провайдера,
    бэкенд получает только токен.
    """

    provider: Optional[str] = None
    kind: PaymentMethodKind = PaymentMethodKind.CARD
    token: Optional[str] = Field(None, max_length=255, description="Токен от провайдера")
    make_default: bool = True


class PaymentResponse(BaseModel):
    """Платёж в истории."""

    id: int
    plan_code: Optional[str] = None
    kind: PaymentKind
    amount: float
    currency: str
    status: PaymentStatus
    provider: str
    failure_reason: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProviderInfo(BaseModel):
    """Что умеет провайдер — фронтенд по этому списку рисует способы оплаты."""

    code: str
    title: str
    methods: List[PaymentMethodKind] = Field(default_factory=list)
    is_configured: bool
    is_default: bool = False
    is_mock: bool = False
