"""Контракт платёжного провайдера.

Биллинг не знает, как именно списываются деньги: он просит провайдера создать
сессию оплаты, а результат — подтверждение или отказ — приходит либо сразу (мок),
либо вебхуком (реальный эквайринг). Поэтому новый провайдер (Stripe, крипто,
эквайринг банка) — это новый класс с этим интерфейсом и регистрация в реестре.
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
    """Результат создания сессии оплаты у провайдера."""

    provider_reference: str
    #: Куда отправить пользователя; ``None`` — провайдер подтверждает платёж сразу
    checkout_url: Optional[str] = None
    requires_redirect: bool = False
    raw: dict = field(default_factory=dict)


@dataclass
class PaymentResult:
    """Итоговая проверка платежа у провайдера."""

    approved: bool
    provider_reference: str
    failure_reason: Optional[str] = None
    raw: dict = field(default_factory=dict)


@dataclass
class AttachedMethod:
    """Способ оплаты, привязанный у провайдера."""

    provider_reference: str
    kind: PaymentMethodKind = PaymentMethodKind.CARD
    brand: Optional[str] = None
    last4: Optional[str] = None
    raw: dict = field(default_factory=dict)


class PaymentProvider(ABC):
    """Интерфейс платёжного провайдера."""

    #: Код провайдера в API и в базе (mock, stripe, crypto)
    code: str = "abstract"
    #: Название для интерфейса
    title: str = "Abstract provider"
    #: Какие способы оплаты поддерживает
    methods: List[PaymentMethodKind] = [PaymentMethodKind.CARD]
    #: Мок-провайдер: подтверждает платежи без внешнего вызова
    is_mock: bool = False

    @abstractmethod
    async def create_checkout(
        self, *, user_id, amount: float, currency: str, plan_code: str, return_url: str
    ) -> CheckoutSession:
        """Создаёт платёжную сессию и возвращает ссылку на оплату."""

    @abstractmethod
    async def confirm(self, provider_reference: str) -> PaymentResult:
        """Запрашивает у провайдера итоговый статус платежа."""

    @abstractmethod
    async def attach_method(
        self, *, user_id, token: Optional[str] = None
    ) -> AttachedMethod:
        """Привязывает способ оплаты: карта вводится на стороне провайдера."""

    @abstractmethod
    async def refund(self, provider_reference: str) -> PaymentResult:
        """Возврат средств по платежу."""

    def verify_webhook(self, payload: bytes, signature: Optional[str]) -> bool:
        """Проверка подписи вебхука.

        По умолчанию — «не доверяем»: провайдер обязан переопределить метод,
        иначе вебхук с подделкой сможет активировать подписку.
        """
        return False

    def is_configured(self) -> bool:
        """Настроен ли провайдер (есть ли ключи)."""
        return True

    def describe(self) -> dict:
        return {
            "code": self.code,
            "title": self.title,
            "methods": self.methods,
            "is_configured": self.is_configured(),
            "is_mock": self.is_mock,
        }
