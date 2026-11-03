"""Мок-провайдер: подтверждает любой платёж.

Нужен, чтобы биллинг можно было пройти целиком без реального эквайринга:
сессия оплаты создаётся, платёж подтверждается сразу, подписка активируется.
Для боевого режима достаточно указать ``BILLING_PROVIDER=stripe`` (или другого
провайдера) — код сервиса и API при этом не меняются.
"""

import uuid

from ..models import PaymentMethodKind
from .base import AttachedMethod
from .base import CheckoutSession
from .base import PaymentProvider
from .base import PaymentResult


class MockPaymentProvider(PaymentProvider):
    """Всегда положительное решение по оплате."""

    code = "mock"
    title = "Тестовая оплата (мок)"
    methods = [PaymentMethodKind.CARD, PaymentMethodKind.CRYPTO]
    is_mock = True

    async def create_checkout(
        self, *, user_id, amount: float, currency: str, plan_code: str, return_url: str
    ) -> CheckoutSession:
        # Ссылки на оплату нет: платёж считается подтверждённым сразу
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
        # У мока нет секрета: вебхуки от него принимаются всегда, но и ущерба нет —
        # провайдер всё равно подтверждает любой платёж
        return True
