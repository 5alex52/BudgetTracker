"""Tests for the service-subscriptions tracker: CRUD and base-currency total."""

import uuid
from datetime import datetime

import pytest
from fastapi import HTTPException
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
