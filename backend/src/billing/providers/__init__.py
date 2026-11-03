"""Реестр платёжных провайдеров.

Провайдер выбирается настройкой ``BILLING_PROVIDER``: сервис биллинга спрашивает
реестр, а не знает конкретные классы — подключение реального эквайринга сводится
к регистрации класса и переменной окружения.
"""

from typing import Dict
from typing import List

from src.config import settings

from .base import AttachedMethod
from .base import CheckoutSession
from .base import PaymentProvider
from .base import PaymentResult
from .crypto import CryptoPaymentProvider
from .mock import MockPaymentProvider
from .stripe import StripePaymentProvider

#: Все известные провайдеры: код → экземпляр
PROVIDERS: Dict[str, PaymentProvider] = {
    provider.code: provider
    for provider in (
        MockPaymentProvider(),
        StripePaymentProvider(),
        CryptoPaymentProvider(),
    )
}


def get_provider(code: str | None = None) -> PaymentProvider:
    """Провайдер по коду; по умолчанию — из настроек.

    Если выбранный реальный провайдер не настроен (нет ключей), падаем громко:
    тихо подменять его моком нельзя — пользователь решит, что заплатил.
    """
    resolved = (code or settings.BILLING_PROVIDER or "mock").lower()
    provider = PROVIDERS.get(resolved)
    if provider is None:
        raise ValueError(f"Unknown payment provider: {resolved}")
    return provider


def list_providers() -> List[PaymentProvider]:
    return list(PROVIDERS.values())


__all__ = [
    "PROVIDERS",
    "get_provider",
    "list_providers",
    "PaymentProvider",
    "CheckoutSession",
    "PaymentResult",
    "AttachedMethod",
]
