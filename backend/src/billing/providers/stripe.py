"""Точка подключения Stripe.

Реализации нет намеренно: платёжные ключи не должны появляться в репозитории, а
проверить реальный платежи без аккаунта Stripe нельзя. Класс описывает, что нужно
сделать при подключении, и до тех пор честно отвечает ``is_configured() == False``
— биллинг не выберет его по умолчанию.
"""

from typing import List
from typing import Optional

from src.config import settings

from ..models import PaymentMethodKind
from .base import AttachedMethod
from .base import CheckoutSession
from .base import PaymentProvider
from .base import PaymentResult


class StripePaymentProvider(PaymentProvider):
    """Карточный эквайринг через Stripe (checkout sessions + webhooks)."""

    code = "stripe"
    title = "Банковская карта (Stripe)"
    methods = [PaymentMethodKind.CARD]
    is_mock = False

    def is_configured(self) -> bool:
        return bool(settings.STRIPE_SECRET_KEY)

    async def create_checkout(
        self, *, user_id, amount: float, currency: str, plan_code: str, return_url: str
    ) -> CheckoutSession:
        # При подключении: stripe.checkout.Session.create(
        #   mode="subscription" | "payment", line_items=[...], client_reference_id=str(user_id),
        #   success_url=return_url, cancel_url=return_url, metadata={"plan_code": plan_code})
        raise NotImplementedError(
            "Stripe не подключён: задайте STRIPE_SECRET_KEY и реализуйте create_checkout через "
            "stripe.checkout.Session.create"
        )

    async def confirm(self, provider_reference: str) -> PaymentResult:
        # При подключении: stripe.checkout.Session.retrieve(provider_reference)
        raise NotImplementedError(
            "Stripe не подключён: confirm через stripe.checkout.Session.retrieve"
        )

    async def attach_method(self, *, user_id, token=None) -> AttachedMethod:
        # При подключении: stripe.PaymentMethod.attach(token, customer=...) + сохранение id
        raise NotImplementedError(
            "Stripe не подключён: attach_method через stripe.PaymentMethod.attach"
        )

    async def refund(self, provider_reference: str) -> PaymentResult:
        raise NotImplementedError(
            "Stripe не подключён: refund через stripe.Refund.create"
        )

    def verify_webhook(self, payload: bytes, signature: Optional[str]) -> bool:
        # При подключении: stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
        if not settings.STRIPE_WEBHOOK_SECRET:
            return False
        return False


#: Список поддерживаемых способов оплаты вынесен явно: фронтенд показывает их иконками
SUPPORTED_METHODS: List[PaymentMethodKind] = StripePaymentProvider.methods
