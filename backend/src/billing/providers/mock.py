"""Mock provider: approves any payment.

Exists so that the billing flow can be completed end-to-end without real acquiring:
a checkout session is created, the payment is confirmed immediately, and the subscription
is activated. For production, just set ``BILLING_PROVIDER=stripe`` (or another provider) —
the service and API code stay the same.
"""

import uuid

from ..models import PaymentMethodKind
from .base import AttachedMethod
from .base import CheckoutSession
from .base import PaymentProvider
from .base import PaymentResult


class MockPaymentProvider(PaymentProvider):
    """Always-approve payment decision."""

    code = "mock"
    title = "Тестовая оплата (мок)"
    methods = [PaymentMethodKind.CARD, PaymentMethodKind.CRYPTO]
    is_mock = True

    async def create_checkout(
        self, *, user_id, amount: float, currency: str, plan_code: str, return_url: str
    ) -> CheckoutSession:
        # No payment link: payment is considered confirmed immediately
        return CheckoutSession(
            provider_reference=f"mock_{uuid.uuid4().hex[:16]}",
            checkout_url=None,
            requires_redirect=False,
            raw={
                "user_id": str(user_id),
                "amount": amount,
                "currency": currency,
                "plan_code": plan_code,
            },
        )

    async def confirm(self, provider_reference: str) -> PaymentResult:
        return PaymentResult(
            approved=True,
            provider_reference=provider_reference,
            raw={"status": "succeeded", "mock": True},
        )

    async def attach_method(self, *, user_id, token=None) -> AttachedMethod:
        return AttachedMethod(
            provider_reference=f"mock_pm_{uuid.uuid4().hex[:16]}",
            kind=PaymentMethodKind.CARD,
            brand="Test",
            last4="4242",
            raw={"user_id": str(user_id), "token": token, "mock": True},
        )

    async def refund(self, provider_reference: str) -> PaymentResult:
        return PaymentResult(
            approved=True,
            provider_reference=provider_reference,
            raw={"status": "refunded", "mock": True},
        )

    def verify_webhook(self, payload: bytes, signature=None) -> bool:
        # Mock has no secret: its webhooks are always accepted, but there is no harm either —
        # the provider approves any payment anyway
        return True
