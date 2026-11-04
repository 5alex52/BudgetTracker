"""Billing HTTP layer."""

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
    """Plan catalog. Public: shown before login."""
    return await BillingViewSet.plans(request=request, session_maker=session_maker)


@billing_router.get("/providers", status_code=status.HTTP_200_OK, response_model=List[ProviderInfo])
async def get_providers(request: Request) -> List[ProviderInfo]:
    """Available payment providers and their status."""
    return await BillingViewSet.providers(request=request)


@billing_router.get("/subscription", status_code=status.HTTP_200_OK, response_model=SubscriptionResponse)
async def get_subscription(
    request: Request,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> SubscriptionResponse:
    """Current subscription; falls back to free plan when absent."""
    return await BillingViewSet.subscription(request=request, user=user, session_maker=session_maker)


@billing_router.get("/entitlements", status_code=status.HTTP_200_OK, response_model=Entitlements)
async def get_entitlements(
    request: Request,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Entitlements:
    """Limits and premium features of the current plan."""
    return await BillingViewSet.entitlements(request=request, user=user, session_maker=session_maker)


@billing_router.post("/subscription", status_code=status.HTTP_200_OK, response_model=CheckoutSession)
async def change_subscription(
    request: Request,
    payload: SubscriptionChangeRequest,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> CheckoutSession:
    """Subscribe to a plan.

    The mock provider confirms the payment immediately and returns
    ``requires_redirect=False``; a real acquirer returns a payment link,
    and the subscription is activated via webhook.
    """
    return await BillingViewSet.change_plan(request=request, user=user, payload=payload, session_maker=session_maker)


@billing_router.delete("/subscription", status_code=status.HTTP_200_OK, response_model=SubscriptionResponse)
async def cancel_subscription(
    request: Request,
    user: CurrentUser,
    immediately: bool = Query(False, description="Cancel immediately instead of at the end of the period"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> SubscriptionResponse:
    """Cancel subscription: by default remains active until the end of the paid period."""
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
    """Saved payment methods."""
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
    """Attach a payment method using a provider token."""
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
    """Set a payment method as default."""
    return await BillingViewSet.set_default(request=request, user=user, obj_id=method_id, session_maker=session_maker)


@billing_router.delete("/payment-methods/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payment_method(
    request: Request,
    method_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> None:
    """Delete a payment method."""
    await BillingViewSet.delete_method(request=request, user=user, obj_id=method_id, session_maker=session_maker)


@billing_router.get("/payments", status_code=status.HTTP_200_OK, response_model=List[PaymentResponse])
async def get_payments(
    request: Request,
    user: CurrentUser,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[PaymentResponse]:
    """User payment history."""
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
    """Payment provider webhook.

    The mock does not verify the signature; real providers verify it with a
    secret from settings. The endpoint exists in advance so that connecting
    Stripe or crypto processing does not require changing the API.
    """
    # Read the body as-is: signature is computed over the original bytes, not the model
    payload = await request.body()
    result = await BillingService.handle_webhook(
        provider_code=provider_code,
        payload=payload,
        signature=signature,
        session_maker=session_maker,
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": result.value})
