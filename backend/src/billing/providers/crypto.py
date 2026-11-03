"""Точка подключения криптоплатежей.

Аналог страйпа для крипты (Coinbase Commerce, NowPayments, Cryptomus): платёж
создаётся как «инвойс» с адресом и суммой в монете, подтверждение приходит
вебхуком после нужного числа подтверждений в сети.
"""

from src.config import settings

from ..models import PaymentMethodKind
from .base import AttachedMethod
from .base import CheckoutSession
from .base import PaymentProvider
from .base import PaymentProvider as _Base
from .base import PaymentResult


class CryptoPaymentProvider(PaymentProvider):
    """Оплата криптовалютой через сторонний процессинг."""

    code = "crypto"
    title = "Криптовалюта (USDT, BTC, ETH)"
    methods = [PaymentMethodKind.CRYPTO]
    is_mock = False

    def is_configured(self) -> bool:
        return bool(settings.CRYPTO_API_KEY)

    async def create_checkout(
        self, *, user_id, amount: float, currency: str, plan_code: str, return_url: str
    ) -> CheckoutSession:
        # При подключении: POST /invoice {price_amount, price_currency, order_id, success_url}
        # → ответ содержит invoice_url и id инвойса
        raise NotImplementedError("Крипто-провайдер не подключён: задайте CRYPTO_API_KEY и реализуйте создание инвойса")

    async def confirm(self, provider_reference: str) -> PaymentResult:
        # При подключении: GET /invoice/{id} — статус waiting|confirming|confirmed|failed
        raise NotImplementedError("Крипто-провайдер не подключён: confirm через статус инвойса")

    async def attach_method(self, *, user_id, token=None) -> AttachedMethod:
        # У крипты нет «сохранённых карт»: привязка кошелька не поддерживается
        raise NotImplementedError("Крипто-провайдер не поддерживает сохранение способа оплаты")

    async def refund(self, provider_reference: str) -> PaymentResult:
        # Возврат в крипте делается вручную через кабинет процессинга
        raise NotImplementedError("Крипто-провайдер возвращает средства вручную")

    def verify_webhook(self, payload: bytes, signature=None) -> bool:
        if not settings.CRYPTO_WEBHOOK_SECRET:
            return False
        return False


# Явная ссылка на базовый класс нужна линтерам: интерфейс импортируется дважды
_ = _Base
