"""Tests for the service-subscriptions tracker: CRUD, totals and auto charges."""

import uuid
from datetime import datetime
from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from src.finance.models import AccountModel
from src.finance.models import CategoryModel
from src.finance.models import ServiceSubRuleModel
from src.finance.models import ServiceSubscriptionModel
from src.finance.models import TransactionModel
from src.finance.schemas import CategoryType
from src.finance.schemas import ServiceSubCreate
from src.finance.schemas import ServiceSubUpdate
from src.finance.schemas import SubscriptionFrequency
from src.finance.service_subs import ServiceSubService
from src.finance.service_subs import run_due_rules_once
from src.finance.utils import calculate_next_payment_date

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
    # A backdated subscription catches up immediately at creation.
    assert created.next_payment_date > datetime.now()

    listing = await ServiceSubService.list_for_user(user.id, session_maker)
    charges = listing.items[0].charges
    assert charges and charges[-1].date == START

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
    # A future start bills nothing at creation; collect is tested in isolation.
    start = datetime.now() + timedelta(days=10)
    created = await ServiceSubService.create_for_user(
        ServiceSubCreate(name="Spotify", price=10.0, currency_id="USD", started_at=start, account_id=account.id),
        user.id,
        session_maker,
    )
    due = datetime.now() - timedelta(days=3)
    async with session_maker() as session:
        sub = await session.get(ServiceSubscriptionModel, created.id)
        sub.next_payment_date = due
        rule = (
            (await session.execute(select(ServiceSubRuleModel).where(ServiceSubRuleModel.service_sub_id == created.id)))
            .scalars()
            .one()
        )
        rule.next_payment_date = due
        await session.commit()

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
        sub.next_payment_date = due
        rule = (
            (await session.execute(select(ServiceSubRuleModel).where(ServiceSubRuleModel.service_sub_id == created.id)))
            .scalars()
            .one()
        )
        rule.next_payment_date = due
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
            started_at=datetime.now() + timedelta(days=10),
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


@pytest.mark.asyncio
async def test_same_day_subscription_bills_immediately(user, currencies, account, session_maker):
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    created = await ServiceSubService.create_for_user(
        ServiceSubCreate(name="SameDay", price=10.0, currency_id="USD", started_at=today, account_id=account.id),
        user.id,
        session_maker,
    )

    assert created.next_payment_date > datetime.now()
    async with session_maker() as session:
        rows = (
            (await session.execute(select(TransactionModel).where(TransactionModel.service_sub_id == created.id)))
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].date == today
        refreshed = await session.get(AccountModel, account.id)
        assert refreshed.balance == pytest.approx(990.0)


@pytest.mark.asyncio
async def test_rule_created_on_attach(user, currencies, account, session_maker):
    start = datetime.now() + timedelta(days=10)
    created = await ServiceSubService.create_for_user(
        ServiceSubCreate(name="RuleSub", price=5.0, currency_id="USD", started_at=start, account_id=account.id),
        user.id,
        session_maker,
    )

    assert created.frequency == "monthly"
    assert created.rule_active is True
    async with session_maker() as session:
        rule = (
            (await session.execute(select(ServiceSubRuleModel).where(ServiceSubRuleModel.service_sub_id == created.id)))
            .scalars()
            .one()
        )
        assert rule.frequency.value == "monthly"
        assert rule.is_active is True
        assert rule.next_payment_date == start


@pytest.mark.asyncio
async def test_rule_cascades_on_delete(user, currencies, account, session_maker):
    created = await ServiceSubService.create_for_user(
        ServiceSubCreate(
            name="RuleSub",
            price=5.0,
            currency_id="USD",
            started_at=datetime.now() + timedelta(days=10),
            account_id=account.id,
        ),
        user.id,
        session_maker,
    )

    await ServiceSubService.delete_for_user(created.id, user.id, session_maker)

    async with session_maker() as session:
        rule = (
            (await session.execute(select(ServiceSubRuleModel).where(ServiceSubRuleModel.service_sub_id == created.id)))
            .scalars()
            .one_or_none()
        )
        assert rule is None


@pytest.mark.asyncio
async def test_paused_rule_does_not_bill(user, currencies, account, session_maker):
    created = await ServiceSubService.create_for_user(
        ServiceSubCreate(
            name="Paused",
            price=5.0,
            currency_id="USD",
            started_at=datetime.now() + timedelta(days=10),
            account_id=account.id,
        ),
        user.id,
        session_maker,
    )
    paused = await ServiceSubService.update_for_user(
        created.id, ServiceSubUpdate(rule_active=False), user.id, session_maker
    )
    assert paused.rule_active is False

    async with session_maker() as session:
        rule = (
            (await session.execute(select(ServiceSubRuleModel).where(ServiceSubRuleModel.service_sub_id == created.id)))
            .scalars()
            .one()
        )
        rule.next_payment_date = datetime.now() - timedelta(days=3)
        await session.commit()

    result = await ServiceSubService.collect_due(user.id, session_maker)

    assert result.created == 0


@pytest.mark.asyncio
async def test_run_due_rules_once_bills_due(user, currencies, account, session_maker):
    created = await ServiceSubService.create_for_user(
        ServiceSubCreate(
            name="Scheduler",
            price=5.0,
            currency_id="USD",
            started_at=datetime.now() + timedelta(days=10),
            account_id=account.id,
        ),
        user.id,
        session_maker,
    )
    async with session_maker() as session:
        rule = (
            (await session.execute(select(ServiceSubRuleModel).where(ServiceSubRuleModel.service_sub_id == created.id)))
            .scalars()
            .one()
        )
        rule.next_payment_date = datetime.now() - timedelta(days=3)
        await session.commit()

    created_count = await run_due_rules_once(session_maker)

    assert created_count >= 1


@pytest.mark.asyncio
async def test_quarterly_frequency_creates_rule_and_bills_every_three_months(user, currencies, account, session_maker):
    # Month-end clamping: Jan 31 + 3 months lands on Apr 30
    assert calculate_next_payment_date(SubscriptionFrequency.QUARTERLY, datetime(2026, 1, 31)) == datetime(2026, 4, 30)

    start = datetime.now() + timedelta(days=10)
    created = await ServiceSubService.create_for_user(
        ServiceSubCreate(
            name="Quarterly",
            price=30.0,
            currency_id="USD",
            started_at=start,
            account_id=account.id,
            frequency=SubscriptionFrequency.QUARTERLY,
        ),
        user.id,
        session_maker,
    )

    assert created.frequency == "quarterly"
    due = datetime.now() - timedelta(days=3)
    async with session_maker() as session:
        rule = (
            (await session.execute(select(ServiceSubRuleModel).where(ServiceSubRuleModel.service_sub_id == created.id)))
            .scalars()
            .one()
        )
        assert rule.frequency == SubscriptionFrequency.QUARTERLY
        rule.next_payment_date = due
        sub = await session.get(ServiceSubscriptionModel, created.id)
        sub.next_payment_date = due
        await session.commit()

    result = await ServiceSubService.collect_due(user.id, session_maker)

    assert result.created == 1
    async with session_maker() as session:
        sub = await session.get(ServiceSubscriptionModel, created.id)
        assert sub.next_payment_date == calculate_next_payment_date(SubscriptionFrequency.QUARTERLY, due)


@pytest.mark.asyncio
async def test_update_frequency_to_yearly(user, currencies, account, session_maker):
    created = await ServiceSubService.create_for_user(
        ServiceSubCreate(
            name="Yearly",
            price=60.0,
            currency_id="USD",
            started_at=datetime.now() + timedelta(days=10),
            account_id=account.id,
        ),
        user.id,
        session_maker,
    )
    assert created.frequency == "monthly"

    updated = await ServiceSubService.update_for_user(
        created.id, ServiceSubUpdate(frequency=SubscriptionFrequency.YEARLY), user.id, session_maker
    )

    assert updated.frequency == "yearly"
    async with session_maker() as session:
        rule = (
            (await session.execute(select(ServiceSubRuleModel).where(ServiceSubRuleModel.service_sub_id == created.id)))
            .scalars()
            .one()
        )
        assert rule.frequency == SubscriptionFrequency.YEARLY
