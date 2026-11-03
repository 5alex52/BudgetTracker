"""ViewSet биллинга: тарифы, подписка, способы оплаты, платежи."""

from typing import List

from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.database import get_async_session_maker
from src.users.schemas import User
from src.viewset import BaseViewSet
from src.viewset import check_permissions

from .models import PaymentMethodKind
from .permissions import BillingPermission
from .schemas import CheckoutSession
from .schemas import Entitlements
from .schemas import PaymentMethodCreate
from .schemas import PaymentMethodResponse
from .schemas import PaymentResponse
from .schemas import PlanResponse
from .schemas import ProviderInfo
from .schemas import SubscriptionChangeRequest
from .schemas import SubscriptionResponse
from .service import BillingService


class BillingViewSet(BaseViewSet[int, PaymentMethodCreate, PaymentMethodCreate]):
    permission = BillingPermission
    service = BillingService

    @classmethod
    @check_permissions(action="list_plans")
    async def plans(
        cls,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> List[PlanResponse]:
        return await cls.service.get_plans(session_maker=session_maker)

    @classmethod
    @check_permissions(action="list_providers")
    async def providers(cls, **kwargs) -> List[ProviderInfo]:
        return cls.service.get_providers()

    @classmethod
    @check_permissions(action="retrieve_subscription")
    async def subscription(
        cls,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> SubscriptionResponse:
        return await cls.service.get_subscription(
            user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="retrieve_entitlements")
    async def entitlements(
        cls,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> Entitlements:
        return await cls.service.get_entitlements(
            user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="change_subscription")
    async def change_plan(
        cls,
        user: User,
        payload: SubscriptionChangeRequest,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> CheckoutSession:
        return await cls.service.change_plan(
            user_id=user.id, request=payload, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="cancel_subscription")
    async def cancel(
        cls,
        user: User,
        immediately: bool = False,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> SubscriptionResponse:
        return await cls.service.cancel_subscription(
            user_id=user.id, immediately=immediately, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="list_payment_methods")
    async def payment_methods(
        cls,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> List[PaymentMethodResponse]:
        return await cls.service.get_payment_methods(
            user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="create_payment_method")
    async def attach_method(
        cls,
        user: User,
        payload: PaymentMethodCreate,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> PaymentMethodResponse:
        return await cls.service.attach_payment_method(
            user_id=user.id,
            provider_code=payload.provider,
            kind=payload.kind or PaymentMethodKind.CARD,
            token=payload.token,
            make_default=payload.make_default,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="delete_payment_method")
    async def delete_method(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> None:
        await cls.service.delete_payment_method(
            user_id=user.id, method_id=obj_id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="update_payment_method")
    async def set_default(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> PaymentMethodResponse:
        return await cls.service.set_default_payment_method(
            user_id=user.id, method_id=obj_id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="list_payments")
    async def payments(
        cls,
        user: User,
        offset: int = 0,
        limit: int = 100,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> List[PaymentResponse]:
        return await cls.service.get_payments(
            user_id=user.id, offset=offset, limit=limit, session_maker=session_maker
        )
