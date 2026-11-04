"""Payment provider contract.

The billing module does not know how money is actually charged: it asks the provider to create
a checkout session, and the result — approval or rejection — comes either immediately (mock) or
via webhook (real acquiring). So a new provider (Stripe, crypto, bank acquiring) is just a new
class with this interface plus registration in the registry.
"""

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field
from typing import List
from typing import Optional

from ..models import PaymentMethodKind


@dataclass
class CheckoutSession:
    """Result of creating a checkout session with the provider."""

    provider_reference: str
    #: Where to send the user; ``None`` — provider confirms payment immediately
    checkout_url: Optional[str] = None
    requires_redirect: bool = False
    raw: dict = field(default_factory=dict)


@dataclass
class PaymentResult:
    """Final payment verification with the provider."""

    approved: bool
    provider_reference: str
    failure_reason: Optional[str] = None
    raw: dict = field(default_factory=dict)


@dataclass
class AttachedMethod:
    """Payment method attached to the provider."""

    provider_reference: str
    kind: PaymentMethodKind = PaymentMethodKind.CARD
    brand: Optional[str] = None
    last4: Optional[str] = None
    raw: dict = field(default_factory=dict)


class PaymentProvider(ABC):
    """Payment provider interface."""

    #: Provider code in the API and database (mock, stripe, crypto)
    code: str = "abstract"
    #: Title for the UI
    title: str = "Abstract provider"
    #: Supported payment methods
    methods: List[PaymentMethodKind] = [PaymentMethodKind.CARD]
    #: Mock provider: approves payments without an external call
    is_mock: bool = False

    @abstractmethod
    async def create_checkout(
        self, *, user_id, amount: float, currency: str, plan_code: str, return_url: str
    ) -> CheckoutSession:
        """Creates a payment session and returns the payment link."""

    @abstractmethod
    async def confirm(self, provider_reference: str) -> PaymentResult:
        """Requests the final payment status from the provider."""

    @abstractmethod
    async def attach_method(self, *, user_id, token: Optional[str] = None) -> AttachedMethod:
        """Attaches a payment method: card is entered on the provider's side."""

    @abstractmethod
    async def refund(self, provider_reference: str) -> PaymentResult:
        """Refund a payment."""

    def verify_webhook(self, payload: bytes, signature: Optional[str]) -> bool:
        """Verify webhook signature.

        Default is "don't trust": the provider must override the method,
        otherwise a forged webhook could activate a subscription.
        """
        return False

    def is_configured(self) -> bool:
        """Whether the provider is configured (keys are present)."""
        return True

    def describe(self) -> dict:
        return {
            "code": self.code,
            "title": self.title,
            "methods": self.methods,
            "is_configured": self.is_configured(),
            "is_mock": self.is_mock,
        }
