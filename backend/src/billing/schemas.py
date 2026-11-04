"""Billing schemas: plans, subscription, payment methods, payments."""

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
    """Plan for the Plans & Payments screen."""

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
    """User's current subscription."""

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
    """What is available to the user based on their plan.

    The single source of truth for limits: both the server (creating accounts, currencies) and
    the client (premium widgets) read the same response, so "subscription is active but widgets
    didn't appear" will not happen again.
    """

    plan_code: str
    plan_name: str
    is_paid: bool = False
    is_active: bool = False
    #: ``None`` — no limit
    max_accounts: Optional[int] = None
    multi_currency: bool = False
    advanced_analytics: bool = False
    current_period_end: Optional[datetime] = None
    reason: Optional[str] = None


class SubscriptionChangeRequest(BaseModel):
    """Subscribe or change plan."""

    plan_code: str = Field(..., min_length=1, max_length=32)
    provider: Optional[str] = Field(None, description="Payment provider; defaults to settings")
    return_url: Optional[str] = Field(None, description="Where to redirect the user after payment")


class CheckoutSession(BaseModel):
    """Checkout session: link to the provider's page and payment data."""

    payment_id: int
    status: PaymentStatus
    provider: str
    provider_reference: Optional[str] = None
    checkout_url: Optional[str] = None
    #: Mock provider confirms payment immediately — no redirect needed on the frontend
    requires_redirect: bool = False
    subscription: Optional[SubscriptionResponse] = None


class PaymentMethodResponse(BaseModel):
    """Saved payment method."""

    id: int
    provider: str
    kind: PaymentMethodKind
    brand: Optional[str] = None
    last4: Optional[str] = None
    is_default: bool = False
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PaymentMethodCreate(BaseModel):
    """Attach a payment method.

    Card data does not come here: number and CVC are entered on the provider's side,
    the backend only receives a token.
    """

    provider: Optional[str] = None
    kind: PaymentMethodKind = PaymentMethodKind.CARD
    token: Optional[str] = Field(None, max_length=255, description="Token from the provider")
    make_default: bool = True


class PaymentResponse(BaseModel):
    """Payment in history."""

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
    """What the provider supports — the frontend renders payment methods based on this list."""

    code: str
    title: str
    methods: List[PaymentMethodKind] = Field(default_factory=list)
    is_configured: bool
    is_default: bool = False
    is_mock: bool = False
