"""Tracked service subscriptions (Netflix, Spotify, ...): CRUD, totals, auto charges.

A vertical slice like ``templates.py``: DAO -> service -> router in one module.
Prices are stored as entered; conversion to the user's base currency uses the
same rates as the rest of the app (personal overrides first, catalog second).
When an account is attached, the subscription bills itself monthly: ``collect``
writes expense records for every date that has come and advances the schedule.
"""

import uuid
from datetime import datetime
from datetime import timedelta
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_async_session_maker

from .dependencies import CurrentUser
from .models import CategoryModel
from .models import ServiceSubscriptionModel
from .models import TransactionModel
from .schemas import CategoryCreate
from .schemas import CategoryType
from .schemas import ServiceSubCharge
from .schemas import ServiceSubCollect
from .schemas import ServiceSubCreate
from .schemas import ServiceSubList
from .schemas import ServiceSubMonthTotal
from .schemas import ServiceSubResponse
from .schemas import ServiceSubUpdate
from .schemas import SubscriptionFrequency
from .schemas import TransactionCreate
from .schemas import TransactionType
from .service import CategoryService
from .service import TransactionService
from .service import _resolve_base_code
from .service import _resolve_base_rate
from .utils import calculate_next_payment_date
from .utils import convert_amount

service_subs_router = APIRouter(
    prefix="/api/finance/service-subs",
    tags=["Service Subs"],
)

#: Recent charges shown per subscription in the list response.
CHARGES_SHOWN = 12


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


def _first_due_date(started_at: datetime) -> datetime:
    """First monthly charge date strictly after today, anchored on the start date."""
    due = started_at
    now = datetime.now()
    while due <= now:
        due = calculate_next_payment_date(SubscriptionFrequency.MONTHLY, due)
    return due


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
        account_id=sub.account_id,
        next_payment_date=sub.next_payment_date,
        created_at=sub.created_at,
        updated_at=sub.updated_at,
    )


class ServiceSubService:
    dao = ServiceSubDAO

    @classmethod
    async def _ensure_category(cls, session: AsyncSession, name: str, user_id, session_maker) -> int:
        """Expense category named after the service; created on first attach."""
        existing = (
            (
                await session.execute(
                    select(CategoryModel)
                    .where(
                        CategoryModel.user_id == user_id,
                        CategoryModel.name == name,
                        CategoryModel.type == CategoryType.EXPENSE,
                    )
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        if existing is not None:
            return existing.id
        category = await CategoryService.create_for_user(
            schema=CategoryCreate(name=name, type=CategoryType.EXPENSE),
            user_id=user_id,
            session_maker=session_maker,
        )
        return category.id

    @classmethod
    async def _checked_account(cls, session: AsyncSession, account_id: int, user_id) -> None:
        from .dao import AccountDAO

        if await AccountDAO.find_one_by_user(session, account_id, user_id) is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account not found")

    @classmethod
    async def list_for_user(cls, user_id, session_maker: async_sessionmaker) -> ServiceSubList:
        async with session_maker() as session:
            subs = await cls.dao.find_all_by_user(session, user_id)
            base_code, base_rate, rates = await _rates(session, user_id)
            items = [_to_response(sub, base_code, base_rate, rates) for sub in subs]
            if subs:
                rows = (
                    (
                        await session.execute(
                            select(TransactionModel)
                            .where(TransactionModel.service_sub_id.in_([sub.id for sub in subs]))
                            .order_by(TransactionModel.date.desc())
                        )
                    )
                    .scalars()
                    .all()
                )
                buckets: dict = {}
                for row in rows:
                    bucket = buckets.setdefault(row.service_sub_id, [])
                    if len(bucket) < CHARGES_SHOWN:
                        bucket.append(
                            ServiceSubCharge(
                                id=row.id,
                                date=row.date,
                                amount=row.amount,
                                currency_id=row.currency_id,
                            )
                        )
                for item in items:
                    item.charges = buckets.get(item.id, [])
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
            category_id = None
            next_due = None
            if schema.account_id is not None:
                await cls._checked_account(session, schema.account_id, user_id)
                category_id = await cls._ensure_category(session, schema.name, user_id, session_maker)
                next_due = _first_due_date(schema.started_at)
            values = {**schema.model_dump(), "user_id": user_id}
            values["category_id"] = category_id
            values["next_payment_date"] = next_due
            sub = await cls.dao.create(session, values)
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
            if "account_id" in data:
                account_id = data["account_id"]
                if account_id is None:
                    # Detaching the account stops the schedule; the category stays for history.
                    data["category_id"] = None
                    data["next_payment_date"] = None
                else:
                    await cls._checked_account(session, account_id, user_id)
                    name = data.get("name", sub.name)
                    if sub.account_id != account_id or sub.category_id is None or "name" in data:
                        data["category_id"] = await cls._ensure_category(session, name, user_id, session_maker)
                    if sub.next_payment_date is None or "started_at" in data:
                        data["next_payment_date"] = _first_due_date(data.get("started_at", sub.started_at))
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

    @classmethod
    async def collect_due(cls, user_id, session_maker: async_sessionmaker) -> ServiceSubCollect:
        """Write a charge record for every due date that has passed since the last run."""
        now = datetime.now()
        async with session_maker() as session:
            subs = await cls.dao.find_all_by_user(session, user_id)
            due = [
                (s.id, s.name, s.account_id, s.category_id, float(s.price), s.currency_id, s.next_payment_date)
                for s in subs
                if s.account_id and s.category_id and s.next_payment_date and s.next_payment_date <= now
            ]
        created = 0
        for sub_id, name, account_id, category_id, price, currency_id, due_date in due:
            charge_date = due_date
            while charge_date <= now:
                await TransactionService.create_for_user(
                    schema=TransactionCreate(
                        account_id=account_id,
                        category_id=category_id,
                        amount=price,
                        currency_id=currency_id,
                        type=TransactionType.EXPENSE,
                        date=charge_date,
                        note=name,
                        service_sub_id=sub_id,
                    ),
                    user_id=user_id,
                    session_maker=session_maker,
                )
                created += 1
                charge_date = calculate_next_payment_date(SubscriptionFrequency.MONTHLY, charge_date)
            async with session_maker() as session:
                sub = await session.get(ServiceSubscriptionModel, sub_id)
                if sub is not None:
                    sub.next_payment_date = charge_date
                    await session.commit()
        return ServiceSubCollect(created=created)

    @classmethod
    async def charges_summary(
        cls, user_id, months: int, session_maker: async_sessionmaker
    ) -> List[ServiceSubMonthTotal]:
        """Monthly charge totals across all tracked subscriptions, in base currency."""
        since = datetime.now() - timedelta(days=months * 31 + 3)
        async with session_maker() as session:
            rows = (
                (
                    await session.execute(
                        select(TransactionModel).where(
                            TransactionModel.service_sub_id.in_(
                                select(ServiceSubscriptionModel.id).where(ServiceSubscriptionModel.user_id == user_id)
                            ),
                            TransactionModel.service_sub_id.is_not(None),
                            TransactionModel.date >= since,
                        )
                    )
                )
                .scalars()
                .all()
            )
            base_code, base_rate, rates = await _rates(session, user_id)
        totals: dict = {}
        for row in rows:
            key = row.date.strftime("%Y-%m")
            amount = convert_amount(row.amount, rates.get(row.currency_id, base_rate), base_rate)
            totals[key] = round(totals.get(key, 0.0) + amount, 2)
        points = [ServiceSubMonthTotal(month=key, total=value) for key, value in sorted(totals.items())]
        return points[-months:]


@service_subs_router.get("", status_code=status.HTTP_200_OK, response_model=ServiceSubList)
async def list_service_subs(
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> ServiceSubList:
    """All tracked subscriptions with recent charges and the total in base currency."""
    return await ServiceSubService.list_for_user(user.id, session_maker)


@service_subs_router.post("", status_code=status.HTTP_201_CREATED, response_model=ServiceSubResponse)
async def create_service_sub(
    schema: ServiceSubCreate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> ServiceSubResponse:
    return await ServiceSubService.create_for_user(schema, user.id, session_maker)


@service_subs_router.post("/collect", status_code=status.HTTP_200_OK, response_model=ServiceSubCollect)
async def collect_service_subs(
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> ServiceSubCollect:
    """Create records for subscriptions whose charge date has come."""
    return await ServiceSubService.collect_due(user.id, session_maker)


@service_subs_router.get("/charges-summary", status_code=status.HTTP_200_OK, response_model=List[ServiceSubMonthTotal])
async def service_subs_charges_summary(
    user: CurrentUser,
    months: int = Query(6, ge=1, le=24),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[ServiceSubMonthTotal]:
    """Monthly totals of subscription charges in the base currency."""
    return await ServiceSubService.charges_summary(user.id, months, session_maker)


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
