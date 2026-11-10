"""Tracked service subscriptions (Netflix, Spotify, ...): CRUD + base-currency total.

A vertical slice like ``templates.py``: DAO → service → router in one module.
Prices are stored as entered; conversion to the user's base currency uses the
same rates as the rest of the app (personal overrides first, catalog second).
"""

import uuid
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_async_session_maker
from src.users.schemas import User

from .dependencies import CurrentUser
from .models import ServiceSubscriptionModel
from .schemas import ServiceSubCreate
from .schemas import ServiceSubList
from .schemas import ServiceSubResponse
from .schemas import ServiceSubUpdate
from .service import _resolve_base_code
from .service import _resolve_base_rate
from .utils import convert_amount

service_subs_router = APIRouter(
    prefix="/api/finance/service-subs",
    tags=["Service Subs"],
)


class ServiceSubDAO:
    model = ServiceSubscriptionModel

    @classmethod
    async def find_all_by_user(cls, session: AsyncSession, user_id) -> list[ServiceSubscriptionModel]:
        stmt = select(cls.model).where(cls.model.user_id == user_id).order_by(cls.model.name)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def find_one_by_user(cls, session: AsyncSession, sub_id: int, user_id) -> Optional[ServiceSubscriptionModel]:
        stmt = select(cls.model).where(cls.model.id == sub_id, cls.model.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalars().one_or_none()

    @classmethod
    async def create(cls, session: AsyncSession, values: dict) -> ServiceSubscriptionModel:
        sub = cls.model(**values)
        session.add(sub)
        await session.commit()
        await session.refresh(sub)
        return sub


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")


async def _rates(session: AsyncSession, user_id) -> tuple[str, float, dict]:
    """(base code, base rate, currency -> rate to base) with personal overrides."""
    from .dao import CurrencyDAO
    from .dao import UserCurrencyRateDAO

    base_code = await _resolve_base_code(session, user_id)
    base_rate = await _resolve_base_rate(session, user_id)
    catalog = await CurrencyDAO.find_all_ordered(session, limit=1000)
    overrides = {row.code: float(row.rate) for row in await UserCurrencyRateDAO.find_all_by_user(session, user_id)}
    rates = {currency.code: overrides.get(currency.code, float(currency.exchange_rate_to_base)) for currency in catalog}
    return base_code, base_rate, rates


def _to_response(sub: ServiceSubscriptionModel, base_code: str, base_rate: float, rates: dict) -> ServiceSubResponse:
    price = float(sub.price)
    rate = rates.get(sub.currency_id, base_rate)
    return ServiceSubResponse(
        id=sub.id,
        name=sub.name,
        icon=sub.icon,
        price=price,
        price_base=round(convert_amount(price, rate, base_rate), 2),
        currency_id=sub.currency_id,
        started_at=sub.started_at,
        created_at=sub.created_at,
        updated_at=sub.updated_at,
    )


class ServiceSubService:
    dao = ServiceSubDAO

    @classmethod
    async def list_for_user(cls, user_id, session_maker: async_sessionmaker) -> ServiceSubList:
        async with session_maker() as session:
            subs = await cls.dao.find_all_by_user(session, user_id)
            base_code, base_rate, rates = await _rates(session, user_id)
            items = [_to_response(sub, base_code, base_rate, rates) for sub in subs]
        total = round(sum(item.price_base for item in items), 2)
        return ServiceSubList(items=items, total_base=total, base_currency=base_code)

    @classmethod
    async def create_for_user(
        cls,
        schema: ServiceSubCreate,
        user_id: uuid.UUID,
        session_maker: async_sessionmaker,
    ) -> ServiceSubResponse:
        from .dao import CurrencyDAO

        async with session_maker() as session:
            if await CurrencyDAO.find_one_or_none(session, code=schema.currency_id) is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown currency")
            sub = await cls.dao.create(session, {**schema.model_dump(), "user_id": user_id})
            base_code, base_rate, rates = await _rates(session, user_id)
            return _to_response(sub, base_code, base_rate, rates)

    @classmethod
    async def update_for_user(
        cls,
        sub_id: int,
        schema: ServiceSubUpdate,
        user_id,
        session_maker: async_sessionmaker,
    ) -> ServiceSubResponse:
        from .dao import CurrencyDAO

        async with session_maker() as session:
            sub = await cls.dao.find_one_by_user(session, sub_id, user_id)
            if sub is None:
                raise _not_found()
            data = schema.model_dump(exclude_unset=True)
            currency = data.get("currency_id", sub.currency_id)
            if await CurrencyDAO.find_one_or_none(session, code=currency) is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown currency")
            for field, value in data.items():
                setattr(sub, field, value)
            await session.commit()
            await session.refresh(sub)
            base_code, base_rate, rates = await _rates(session, user_id)
            return _to_response(sub, base_code, base_rate, rates)

    @classmethod
    async def delete_for_user(cls, sub_id: int, user_id, session_maker: async_sessionmaker) -> None:
        async with session_maker() as session:
            sub = await cls.dao.find_one_by_user(session, sub_id, user_id)
            if sub is None:
                raise _not_found()
            await session.delete(sub)
            await session.commit()


@service_subs_router.get("", status_code=status.HTTP_200_OK, response_model=ServiceSubList)
async def list_service_subs(
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> ServiceSubList:
    """All tracked subscriptions plus their total in the base currency."""
    return await ServiceSubService.list_for_user(user.id, session_maker)


@service_subs_router.post("", status_code=status.HTTP_201_CREATED, response_model=ServiceSubResponse)
async def create_service_sub(
    schema: ServiceSubCreate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> ServiceSubResponse:
    return await ServiceSubService.create_for_user(schema, user.id, session_maker)


@service_subs_router.patch("/{sub_id}", status_code=status.HTTP_200_OK, response_model=ServiceSubResponse)
async def update_service_sub(
    sub_id: int,
    schema: ServiceSubUpdate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> ServiceSubResponse:
    return await ServiceSubService.update_for_user(sub_id, schema, user.id, session_maker)


@service_subs_router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_sub(
    sub_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> None:
    await ServiceSubService.delete_for_user(sub_id, user.id, session_maker)
