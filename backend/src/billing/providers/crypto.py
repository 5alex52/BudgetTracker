"""Crypto payment integration.

Analog of Stripe for crypto (Coinbase Commerce, NowPayments, Cryptomus): a payment is created
as an "invoice" with an address and amount in a coin, and confirmation comes via webhook after
the required number of network confirmations.
"""

from src.config import settings

from ..models import PaymentMethodKind
from .base import AttachedMethod
from .base import CheckoutSession
from .base import PaymentProvider
from .base import PaymentProvider as _Base
from .base import PaymentResult


class CryptoPaymentProvider(PaymentProvider):
    """Cryptocurrency payment via third-party processing."""

    code = "crypto"
    title = "Криптовалюта (USDT, BTC, ETH)"
    methods = [PaymentMethodKind.CRYPTO]
    is_mock = False

    def is_configured(self) -> bool:
        return bool(settings.CRYPTO_API_KEY)

    async def create_checkout(
        self, *, user_id, amount: float, currency: str, plan_code: str, return_url: str
    ) -> CheckoutSession:
        # When integrating: POST /invoice {price_amount, price_currency, order_id, success_url}
        # → response contains invoice_url and invoice id
        raise NotImplementedError("Крипто-провайдер не подключён: задайте CRYPTO_API_KEY и реализуйте создание инвойса")

    async def confirm(self, provider_reference: str) -> PaymentResult:
        # When integrating: GET /invoice/{id} — status waiting|confirming|confirmed|failed
        raise NotImplementedError("Крипто-провайдер не подключён: confirm через статус инвойса")

    async def attach_method(self, *, user_id, token=None) -> AttachedMethod:
        # Crypto has no "saved cards": wallet attachment is not supported
        raise NotImplementedError("Крипто-провайдер не поддерживает сохранение способа оплаты")

    async def refund(self, provider_reference: str) -> PaymentResult:
        # Crypto refunds are done manually via the processor's dashboard
        raise NotImplementedError("Крипто-провайдер возвращает средства вручную")

    def verify_webhook(self, payload: bytes, signature=None) -> bool:
        if not settings.CRYPTO_WEBHOOK_SECRET:
            return False
        return False


# Explicit reference to the base class is needed for linters: interface is imported twice
_ = _Base
