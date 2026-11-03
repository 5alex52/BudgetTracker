"""HTTP-слой биллинга."""

from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import Query
from fastapi import Request
from fastapi import status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.database import get_async_session_maker

from .dependencies import CurrentUser
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
from .viewsets import BillingViewSet

billing_router = APIRouter(prefix="/api/billing", tags=["Billing"])


@billing_router.get("/plans", status_code=status.HTTP_200_OK, response_model=List[PlanResponse])
async def get_plans(
    request: Request,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[PlanResponse]:
    """Каталог тарифов. Публичный: показывается до входа."""
    return await BillingViewSet.plans(request=request, session_maker=session_maker)


@billing_router.get("/providers", status_code=status.HTTP_200_OK, response_model=List[ProviderInfo])
async def get_providers(request: Request) -> List[ProviderInfo]:
    """Доступные платёжные провайдеры и их состояние."""
    return await BillingViewSet.providers(request=request)


@billing_router.get("/subscription", status_code=status.HTTP_200_OK, response_model=SubscriptionResponse)
async def get_subscription(
    request: Request,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> SubscriptionResponse:
    """Текущая подписка; без подписки — бесплатный тариф."""
    return await BillingViewSet.subscription(request=request, user=user, session_maker=session_maker)


@billing_router.get("/entitlements", status_code=status.HTTP_200_OK, response_model=Entitlements)
async def get_entitlements(
    request: Request,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Entitlements:
    """Лимиты и премиум-возможности текущего тарифа."""
    return await BillingViewSet.entitlements(request=request, user=user, session_maker=session_maker)


@billing_router.post("/subscription", status_code=status.HTTP_200_OK, response_model=CheckoutSession)
async def change_subscription(
    request: Request,
    payload: SubscriptionChangeRequest,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> CheckoutSession:
    """Оформление тарифа.

    Мок-провайдер подтверждает платёж сразу и возвращает ``requires_redirect=False``;
    реальный эквайринг вернёт ссылку на оплату, а подписка активируется по вебхуку.
    """
    return await BillingViewSet.change_plan(request=request, user=user, payload=payload, session_maker=session_maker)


@billing_router.delete("/subscription", status_code=status.HTTP_200_OK, response_model=SubscriptionResponse)
async def cancel_subscription(
    request: Request,
    user: CurrentUser,
    immediately: bool = Query(False, description="Отключить сразу, а не в конце периода"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> SubscriptionResponse:
    """Отмена подписки: по умолчанию действует до конца оплаченного периода."""
    return await BillingViewSet.cancel(request=request, user=user, immediately=immediately, session_maker=session_maker)


@billing_router.get(
    "/payment-methods",
    status_code=status.HTTP_200_OK,
    response_model=List[PaymentMethodResponse],
)
async def get_payment_methods(
    request: Request,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[PaymentMethodResponse]:
    """Сохранённые способы оплаты."""
    return await BillingViewSet.payment_methods(request=request, user=user, session_maker=session_maker)


@billing_router.post(
    "/payment-methods",
    status_code=status.HTTP_201_CREATED,
    response_model=PaymentMethodResponse,
)
async def attach_payment_method(
    request: Request,
    payload: PaymentMethodCreate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> PaymentMethodResponse:
    """Привязка способа оплаты по токену провайдера."""
    return await BillingViewSet.attach_method(request=request, user=user, payload=payload, session_maker=session_maker)


@billing_router.post(
    "/payment-methods/{method_id}/default",
    status_code=status.HTTP_200_OK,
    response_model=PaymentMethodResponse,
)
async def set_default_payment_method(
    request: Request,
    method_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> PaymentMethodResponse:
    """Сделать способ оплаты основным."""
    return await BillingViewSet.set_default(request=request, user=user, obj_id=method_id, session_maker=session_maker)


@billing_router.delete("/payment-methods/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_method(
    request: Request,
    method_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> None:
    """Удаление способа оплаты."""
    await BillingViewSet.delete_method(request=request, user=user, obj_id=method_id, session_maker=session_maker)


@billing_router.get("/payments", status_code=status.HTTP_200_OK, response_model=List[PaymentResponse])
async def get_payments(
    request: Request,
    user: CurrentUser,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[PaymentResponse]:
    """История платежей пользователя."""
    return await BillingViewSet.payments(
        request=request,
        user=user,
        offset=offset,
        limit=limit,
        session_maker=session_maker,
    )


@billing_router.post("/webhooks/{provider_code}", status_code=status.HTTP_200_OK, include_in_schema=True)
async def provider_webhook(
    request: Request,
    provider_code: str,
    signature: Optional[str] = Header(None, alias="X-Signature"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> JSONResponse:
    """Вебхук платёжного провайдера.

    У мока подпись не проверяется, у реальных провайдеров проверяется секретом из
    настроек. Эндпоинт существует заранее, чтобы подключение Stripe или крипто-
    процессинга не требовало менять API.
    """
    # Тело читаем как есть: подпись считается по исходным байтам, а не по модели
    payload = await request.body()
    result = await BillingService.handle_webhook(
        provider_code=provider_code,
        payload=payload,
        signature=signature,
        session_maker=session_maker,
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": result.value})
