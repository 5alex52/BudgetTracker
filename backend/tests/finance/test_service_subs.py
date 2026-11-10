"""Tests for the service-subscriptions tracker: CRUD, totals and auto charges."""

import uuid
from datetime import datetime
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from src.finance.models import AccountModel
from src.finance.models import CategoryModel
from src.finance.models import ServiceSubscriptionModel
from src.finance.models import TransactionModel
from src.finance.schemas import CategoryType
from src.finance.schemas import ServiceSubCreate
from src.finance.schemas import ServiceSubUpdate
from src.finance.service_subs import ServiceSubService

START = datetime(2026, 1, 15, 12, 0)


def _create(name, price, currency, icon=None):
    return ServiceSubCreate(name=name, price=price, currency_id=currency, started_at=START, icon=icon)


@pytest.mark.asyncio
async def test_service_sub_total_in_base_currency(user, currencies, session_maker):
    await ServiceSubService.create_for_user(_create("Spotify", 10.0, "USD"), user.id, session_maker)
    await ServiceSubService.create_for_user(_create("Deezer", 100.0, "EUR", icon="deezer"), user.id, session_maker)

    listing = await ServiceSubService.list_for_user(user.id, session_maker)

    assert listing.base_currency == "USD"
    assert listing.total_base == pytest.approx(120.0)  # 10 USD + 100 EUR * 1.1
    by_name = {item.name: item for item in listing.items}
    assert by_name["Deezer"].price_base == pytest.approx(110.0)
    assert by_name["Deezer"].icon == "deezer"


@pytest.mark.asyncio
async def test_update_price_and_delete(user, currencies, session_maker):
    created = await ServiceSubService.create_for_user(_create("Xbox", 5.0, "USD"), user.id, session_maker)

    updated = await ServiceSubService.update_for_user(created.id, ServiceSubUpdate(price=7.5), user.id, session_maker)
    assert updated.price == pytest.approx(7.5)

    await ServiceSubService.delete_for_user(created.id, user.id, session_maker)
    listing = await ServiceSubService.list_for_user(user.id, session_maker)
    assert listing.items == []
    assert listing.total_base == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_subscriptions_are_isolated_per_user(user, other_user, currencies, session_maker):
    created = await ServiceSubService.create_for_user(_create("Notion", 4.0, "USD"), user.id, session_maker)

    with pytest.raises(HTTPException) as error:
        await ServiceSubService.update_for_user(created.id, ServiceSubUpdate(price=1.0), other_user.id, session_maker)
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_unknown_currency_rejected(user, currencies, session_maker):
    with pytest.raises(HTTPException) as error:
        await ServiceSubService.create_for_user(_create("AOL", 1.0, "XXX"), user.id, session_maker)
    assert error.value.status_code == 400
    assert "currency" in error.value.detail.lower()


@pytest.mark.asyncio
async def test_attaching_account_schedules_charges(user, currencies, account, session_maker):
    created = await ServiceSubService.create_for_user(
        ServiceSubCreate(name="Netflix", price=10.0, currency_id="USD", started_at=START, account_id=account.id),
        user.id,
        session_maker,
    )

    assert created.account_id == account.id
    assert created.next_payment_date == START  # bills from the start date itself

    async with session_maker() as session:
        category = (
            (
                await session.execute(
                    select(CategoryModel).where(
                        CategoryModel.user_id == user.id,
                        CategoryModel.name == "Netflix",
                        CategoryModel.type == CategoryType.EXPENSE,
                    )
                )
            )
            .scalars()
            .one()
        )
        assert category is not None


@pytest.mark.asyncio
async def test_collect_writes_records_and_advances_schedule(user, currencies, account, session_maker):
    start = datetime.now() - timedelta(days=3)
    created = await ServiceSubService.create_for_user(
        ServiceSubCreate(name="Spotify", price=10.0, currency_id="USD", started_at=start, account_id=account.id),
        user.id,
        session_maker,
    )

    result = await ServiceSubService.collect_due(user.id, session_maker)

    assert result.created == 1
    async with session_maker() as session:
        row = (
            (await session.execute(select(TransactionModel).where(TransactionModel.service_sub_id == created.id)))
            .scalars()
            .one()
        )
        charge_id = row.id
        assert row.note == "Spotify"
        assert row.amount == pytest.approx(10.0)
        refreshed = await session.get(AccountModel, account.id)
        assert refreshed.balance == pytest.approx(990.0)
        sub = await session.get(ServiceSubscriptionModel, created.id)
        assert sub.next_payment_date > datetime.now()

    listing = await ServiceSubService.list_for_user(user.id, session_maker)
    assert listing.items[0].charges[0].id == charge_id

    # rolling the watermark back does not bill the same date twice
    async with session_maker() as session:
        sub = await session.get(ServiceSubscriptionModel, created.id)
        sub.next_payment_date = start
        await session.commit()

    again = await ServiceSubService.collect_due(user.id, session_maker)

    assert again.created == 0


@pytest.mark.asyncio
async def test_charges_summary_totals_in_base_currency(user, currencies, account, session_maker):
    created = await ServiceSubService.create_for_user(
        ServiceSubCreate(
            name="Deezer",
            price=100.0,
            currency_id="EUR",
            started_at=datetime.now() - timedelta(days=3),
            account_id=account.id,
        ),
        user.id,
        session_maker,
    )
    await ServiceSubService.collect_due(user.id, session_maker)

    summary = await ServiceSubService.charges_summary(user.id, 6, session_maker)

    assert summary[-1].month == datetime.now().strftime("%Y-%m")
    assert summary[-1].total == pytest.approx(110.0)  # 100 EUR at catalog rate 1.1


@pytest.mark.asyncio
async def test_deleting_subscription_removes_its_auto_rule(user, currencies, account, session_maker):
    created = await ServiceSubService.create_for_user(
        ServiceSubCreate(
            name="Netflix",
            price=10.0,
            currency_id="USD",
            started_at=datetime.now() - timedelta(days=3),
            account_id=account.id,
        ),
        user.id,
        session_maker,
    )

    await ServiceSubService.delete_for_user(created.id, user.id, session_maker)
    result = await ServiceSubService.collect_due(user.id, session_maker)

    assert result.created == 0
    async with session_maker() as session:
        refreshed = await session.get(AccountModel, account.id)
        assert refreshed.balance == pytest.approx(1000.0)
