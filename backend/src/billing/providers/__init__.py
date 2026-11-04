"""Payment provider registry.

The provider is selected by the ``BILLING_PROVIDER`` setting: the billing service asks the
registry rather than knowing specific classes — connecting real acquiring is reduced to
registering a class and setting an environment variable.
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

#: All known providers: code → instance
PROVIDERS: Dict[str, PaymentProvider] = {
    provider.code: provider
    for provider in (
        MockPaymentProvider(),
        StripePaymentProvider(),
        CryptoPaymentProvider(),
    )
}


def get_provider(code: str | None = None) -> PaymentProvider:
    """Provider by code; defaults to the one from settings.

    If the selected real provider is not configured (no keys), fail loudly:
    silently swapping it with a mock would make the user think they paid.
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
