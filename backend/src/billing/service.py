"""Сервис биллинга: тарифы, подписка, способы оплаты и платежи.

Списание денег делегируется провайдеру (``src/billing/providers``): сервис создаёт
платёж, просит сессию оплаты и активирует подписку только после подтверждения.
Сейчас по умолчанию подключён мок, который подтверждает платёж сразу, поэтому
API возвращает ``requires_redirect=False``; реальный эквайринг вернёт ссылку на
оплату, а подтверждение придёт вебхуком.
"""

import logging
import uuid
from datetime import datetime
from datetime import timedelta
from typing import List
from typing import Optional

from fastapi import HTTPException
from fastapi import status
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.config import settings
from src.database import async_session_maker

from .dao import PaymentDAO
from .dao import PaymentMethodDAO
from .dao import PlanDAO
from .dao import SubscriptionDAO
from .models import PaymentKind
from .models import PaymentMethodKind
from .models import PaymentMethodModel
from .models import PaymentModel
from .models import PaymentStatus
from .models import PlanModel
from .models import PlanPeriod
from .models import PlanSubscriptionModel
from .models import SubscriptionStatus
from .providers import get_provider
from .providers import list_providers
from .providers import PaymentProvider
from .schemas import CheckoutSession
from .schemas import Entitlements
from .schemas import PaymentMethodResponse
from .schemas import PaymentResponse
from .schemas import PlanResponse
from .schemas import ProviderInfo
from .schemas import SubscriptionChangeRequest
from .schemas import SubscriptionResponse

logger = logging.getLogger(__name__)

#: Тариф по умолчанию для всех, кто ещё ничего не оплачивал
FREE_PLAN_CODE = "free"

#: Сколько счетов можно вести на бесплатном тарифе
FREE_MAX_ACCOUNTS = 2


def _not_found(detail: str = "Not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _resolve_session_maker(
    session_maker: Optional[async_sessionmaker],
) -> async_sessionmaker:
    return session_maker or async_session_maker


def _period_end(plan: PlanModel, start: datetime) -> Optional[datetime]:
    """Когда заканчивается оплаченный период тарифа."""
    if plan.period == PlanPeriod.MONTH:
        return start + timedelta(days=30)
    if plan.period == PlanPeriod.YEAR:
        return start + timedelta(days=365)
    return None


class BillingService:
    """Операции биллинга в разрезе пользователя."""

    # ------------------------------------------------------------------ #
    #  Тарифы и провайдеры
    # ------------------------------------------------------------------ #

    @classmethod
    async def get_plans(cls, session_maker: Optional[async_sessionmaker] = None) -> List[PlanResponse]:
        """Каталог тарифов.

        Меняется редко, а спрашивается на каждой странице оплаты — держим в Redis
        пять минут. Кеш необязателен: без Redis ответ просто считается заново.
        """
        from src.cache import Cache

        key = Cache.make_key("billing:plans")
        hit = await Cache.get(key)
        if hit is not None:
            return [PlanResponse(**item) for item in hit]

        plans = await cls._get_plans(session_maker)
        await Cache.set(key, [plan.model_dump() for plan in plans], ttl=300)
        return plans

    @classmethod
    async def _get_plans(cls, session_maker: Optional[async_sessionmaker] = None) -> List[PlanResponse]:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            plans = await PlanDAO.find_all_active(session)
        return [PlanResponse.model_validate(plan) for plan in plans]

    @classmethod
    def get_providers(cls) -> List[ProviderInfo]:
        """Список провайдеров: фронтенд показывает доступные способы оплаты."""
        default_code = (settings.BILLING_PROVIDER or "mock").lower()
        return [
            ProviderInfo(
                code=provider.code,
                title=provider.title,
                methods=list(provider.methods),
                is_configured=provider.is_configured(),
                is_default=provider.code == default_code,
                is_mock=provider.is_mock,
            )
            for provider in list_providers()
        ]

    # ------------------------------------------------------------------ #
    #  Подписка
    # ------------------------------------------------------------------ #

    @classmethod
    async def get_subscription(
        cls, user_id: uuid.UUID, session_maker: Optional[async_sessionmaker] = None
    ) -> SubscriptionResponse:
        """Текущая подписка; если её нет — бесплатный тариф."""
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            subscription = await SubscriptionDAO.find_current(session, user_id)
            if subscription is None:
                return SubscriptionResponse(
                    plan_code=FREE_PLAN_CODE,
                    plan_name="Бесплатный",
                    status=SubscriptionStatus.ACTIVE,
                )
            return cls._subscription_response(subscription)

    @classmethod
    async def get_entitlements(
        cls, user_id: uuid.UUID, session_maker: Optional[async_sessionmaker] = None
    ) -> Entitlements:
        """Права пользователя по тарифу — один ответ и для лимитов, и для UI.

        Просроченная или отменённая подписка не даёт премиум-возможностей:
        пользователь откатывается к бесплатному тарифу, но данные остаются.
        """
        subscription = await cls.get_subscription(user_id, session_maker=session_maker)
        now = datetime.utcnow()

        paid = subscription.plan_code != FREE_PLAN_CODE
        active = subscription.status == SubscriptionStatus.ACTIVE
        until = subscription.current_period_end
        expired = paid and until is not None and until < now
        granted = paid and active and not expired

        if granted:
            return Entitlements(
                plan_code=subscription.plan_code,
                plan_name=subscription.plan_name,
                is_paid=True,
                is_active=True,
                max_accounts=None,
                multi_currency=True,
                advanced_analytics=True,
                current_period_end=until,
            )

        reason = None
        if paid and expired:
            reason = "subscription_expired"
        elif paid and not active:
            reason = "subscription_inactive"

        return Entitlements(
            plan_code=FREE_PLAN_CODE,
            plan_name="Бесплатный",
            is_paid=False,
            is_active=True,
            max_accounts=FREE_MAX_ACCOUNTS,
            multi_currency=False,
            advanced_analytics=False,
            current_period_end=until,
            reason=reason,
        )

    @classmethod
    def _subscription_response(cls, subscription: PlanSubscriptionModel) -> SubscriptionResponse:
        return SubscriptionResponse(
            id=subscription.id,
            plan_code=subscription.plan_code,
            plan_name=(subscription.plan.name if subscription.plan else subscription.plan_code),
            status=subscription.status,
            started_at=subscription.started_at,
            current_period_end=subscription.current_period_end,
            cancel_at_period_end=subscription.cancel_at_period_end,
            provider=subscription.provider,
        )

    @classmethod
    async def change_plan(
        cls,
        user_id: uuid.UUID,
        request: SubscriptionChangeRequest,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> CheckoutSession:
        """Оформление тарифа: создаёт платёж, спрашивает провайдера и активирует подписку.

        Порядок важен: подписка становится активной только после подтверждения
        платежа, иначе пользователь получил бы тариф без оплаты.
        """
        maker = _resolve_session_maker(session_maker)
        provider = get_provider(request.provider)

        async with maker() as session:
            plan = await PlanDAO.find_by_code(session, request.plan_code)
            if plan is None or not plan.is_active:
                raise _not_found("Plan not found")

            if plan.period == PlanPeriod.NONE:
                # Бесплатный тариф не оплачивается: просто фиксируем подписку
                subscription = PlanSubscriptionModel(
                    user_id=user_id,
                    plan_code=plan.code,
                    status=SubscriptionStatus.ACTIVE,
                    provider=provider.code,
                )
                session.add(subscription)
                await session.commit()
                await session.refresh(subscription)
                return CheckoutSession(
                    payment_id=0,
                    status=PaymentStatus.SUCCEEDED,
                    provider=provider.code,
                    requires_redirect=False,
                    subscription=cls._subscription_response(subscription),
                )

            payment = PaymentModel(
                user_id=user_id,
                plan_code=plan.code,
                kind=PaymentKind.SUBSCRIPTION,
                amount=plan.price,
                currency=plan.currency,
                status=PaymentStatus.PENDING,
                provider=provider.code,
            )
            session.add(payment)
            await session.commit()
            await session.refresh(payment)

            try:
                checkout = await provider.create_checkout(
                    user_id=user_id,
                    amount=plan.price,
                    currency=plan.currency,
                    plan_code=plan.code,
                    return_url=request.return_url or settings.BILLING_RETURN_URL,
                )
            except NotImplementedError as error:
                # Провайдер выбран, но не настроен: честно говорим об этом,
                # а не выдаём пользователю подписку без оплаты
                logger.warning("Payment provider %s is not configured: %s", provider.code, error)
                await PaymentDAO.mark(session, payment, PaymentStatus.FAILED, "Provider not configured")
                await session.commit()
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Payment provider '{provider.code}' is not configured",
                )
            payment.provider_reference = checkout.provider_reference
            await session.commit()

            if checkout.requires_redirect:
                # Реальный эквайринг: ждём вебхук, подписку пока не активируем
                return CheckoutSession(
                    payment_id=payment.id,
                    status=payment.status,
                    provider=provider.code,
                    provider_reference=checkout.provider_reference,
                    checkout_url=checkout.checkout_url,
                    requires_redirect=True,
                )

            result = await provider.confirm(checkout.provider_reference)
            if not result.approved:
                await PaymentDAO.mark(session, payment, PaymentStatus.FAILED, result.failure_reason)
                await session.commit()
                return CheckoutSession(
                    payment_id=payment.id,
                    status=PaymentStatus.FAILED,
                    provider=provider.code,
                    provider_reference=checkout.provider_reference,
                )

            subscription = await cls._activate(session, user_id, plan, provider, payment)
            await PaymentDAO.mark(session, payment, PaymentStatus.SUCCEEDED)
            await session.commit()
            await session.refresh(subscription)

        return CheckoutSession(
            payment_id=payment.id,
            status=PaymentStatus.SUCCEEDED,
            provider=provider.code,
            provider_reference=checkout.provider_reference,
            requires_redirect=False,
            subscription=cls._subscription_response(subscription),
        )

    @classmethod
    async def _activate(
        cls,
        session,
        user_id: uuid.UUID,
        plan: PlanModel,
        provider: PaymentProvider,
        payment: PaymentModel,
    ) -> PlanSubscriptionModel:
        """Продлевает текущую подписку или заводит новую."""
        current = await SubscriptionDAO.find_current(session, user_id)
        now = datetime.now()
        if current is not None and current.plan_code == plan.code and current.status == SubscriptionStatus.ACTIVE:
            start = current.current_period_end if current.current_period_end else now
            current.current_period_end = _period_end(plan, start or now)
            current.cancel_at_period_end = False
            current.provider = provider.code
            current.provider_reference = payment.provider_reference
            await session.flush()
            return current

        subscription = PlanSubscriptionModel(
            user_id=user_id,
            plan_code=plan.code,
            status=SubscriptionStatus.ACTIVE,
            started_at=now,
            current_period_end=_period_end(plan, now),
            provider=provider.code,
            provider_reference=payment.provider_reference,
        )
        session.add(subscription)
        await session.flush()
        await session.refresh(subscription)
        return subscription

    @classmethod
    async def cancel_subscription(
        cls,
        user_id: uuid.UUID,
        immediately: bool = False,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> SubscriptionResponse:
        """Отмена подписки: по умолчанию — до конца оплаченного периода."""
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            subscription = await SubscriptionDAO.find_current(session, user_id)
            if subscription is None or subscription.status != SubscriptionStatus.ACTIVE:
                raise _not_found("Active subscription not found")
            if immediately:
                subscription.status = SubscriptionStatus.CANCELED
                subscription.cancel_at_period_end = False
            else:
                subscription.cancel_at_period_end = True
            await session.commit()
            await session.refresh(subscription)
            return cls._subscription_response(subscription)

    # ------------------------------------------------------------------ #
    #  Способы оплаты
    # ------------------------------------------------------------------ #

    @classmethod
    async def get_payment_methods(
        cls, user_id: uuid.UUID, session_maker: Optional[async_sessionmaker] = None
    ) -> List[PaymentMethodResponse]:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            methods = await PaymentMethodDAO.find_all_by_user(session, user_id)
        return [PaymentMethodResponse.model_validate(method) for method in methods]

    @classmethod
    async def attach_payment_method(
        cls,
        user_id: uuid.UUID,
        provider_code: Optional[str] = None,
        kind: PaymentMethodKind = PaymentMethodKind.CARD,
        token: Optional[str] = None,
        make_default: bool = True,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> PaymentMethodResponse:
        """Привязывает способ оплаты через провайдера.

        Номер карты и CVC сюда не попадают: токен выдаёт провайдер на своей форме.
        """
        maker = _resolve_session_maker(session_maker)
        provider = get_provider(provider_code)
        try:
            attached = await provider.attach_method(user_id=user_id, token=token)
        except NotImplementedError as error:
            logger.warning("Payment provider %s cannot attach methods: %s", provider.code, error)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Payment provider '{provider.code}' does not support saved payment methods",
            )

        async with maker() as session:
            if make_default:
                await PaymentMethodDAO.clear_defaults(session, user_id)
            method = PaymentMethodModel(
                user_id=user_id,
                provider=provider.code,
                kind=attached.kind or kind,
                brand=attached.brand,
                last4=attached.last4,
                is_default=make_default,
                provider_reference=attached.provider_reference,
            )
            session.add(method)
            await session.commit()
            await session.refresh(method)
        return PaymentMethodResponse.model_validate(method)

    @classmethod
    async def delete_payment_method(
        cls,
        user_id: uuid.UUID,
        method_id: int,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> None:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            method = await PaymentMethodDAO.find_one_by_user(session, method_id, user_id)
            if method is None:
                raise _not_found("Payment method not found")
            await session.delete(method)
            await session.commit()

    @classmethod
    async def set_default_payment_method(
        cls,
        user_id: uuid.UUID,
        method_id: int,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> PaymentMethodResponse:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            method = await PaymentMethodDAO.find_one_by_user(session, method_id, user_id)
            if method is None:
                raise _not_found("Payment method not found")
            await PaymentMethodDAO.clear_defaults(session, user_id)
            method.is_default = True
            await session.commit()
            await session.refresh(method)
        return PaymentMethodResponse.model_validate(method)

    # ------------------------------------------------------------------ #
    #  Платежи
    # ------------------------------------------------------------------ #

    @classmethod
    async def get_payments(
        cls,
        user_id: uuid.UUID,
        offset: int = 0,
        limit: int = 100,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> List[PaymentResponse]:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            payments = await PaymentDAO.find_all_by_user(session, user_id, offset=offset, limit=limit)
        return [PaymentResponse.model_validate(payment) for payment in payments]

    @classmethod
    async def handle_webhook(
        cls,
        provider_code: str,
        payload: bytes,
        signature: Optional[str],
        session_maker: Optional[async_sessionmaker] = None,
    ) -> PaymentStatus:
        """Обработка вебхука провайдера: подтверждает платёж и активирует подписку.

        Этот путь используется реальным эквайрингом; мок его не требует, но
        эндпоинт существует и покрыт тестом, чтобы подключение провайдера не
        потребовало менять API.
        """
        provider = get_provider(provider_code)
        if not provider.verify_webhook(payload, signature):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook signature",
            )

        import json

        try:
            event = json.loads(payload.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid webhook payload",
            )

        reference = event.get("provider_reference") or event.get("id")
        if not reference:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing payment reference",
            )

        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            payment = await PaymentDAO.find_by_reference(session, reference)
            if payment is None:
                raise _not_found("Payment not found")

            result = await provider.confirm(reference)
            if not result.approved:
                await PaymentDAO.mark(session, payment, PaymentStatus.FAILED, result.failure_reason)
                await session.commit()
                return PaymentStatus.FAILED

            plan = await PlanDAO.find_by_code(session, payment.plan_code) if payment.plan_code else None
            if plan is not None:
                await cls._activate(session, payment.user_id, plan, provider, payment)
            await PaymentDAO.mark(session, payment, PaymentStatus.SUCCEEDED)
            await session.commit()
            return PaymentStatus.SUCCEEDED
