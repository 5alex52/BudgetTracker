"""Tests for personal currency rates."""

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select
from src.finance.models import UserCurrencyRateModel
from src.finance.service import CurrencyService
from src.users.models import UserModel


@pytest.mark.asyncio
async def test_user_rate_overrides_catalog_rate(user, currencies, session_maker):
    await CurrencyService.set_user_rate(code="EUR", rate=2.0, user_id=user.id, session_maker=session_maker)

    rates = await CurrencyService.get_rates(base="USD", user_id=user.id, session_maker=session_maker)
    by_code = {rate.code: rate for rate in rates}

    # Display input "2 EUR per 1 USD" is stored inverted (0.5 USD per EUR)
    # and reads back as the same 2.0 instead of the catalog 1 / 1.1.
    assert by_code["EUR"].rate == pytest.approx(2.0)
    assert by_code["EUR"].is_custom is True
    assert by_code["USD"].is_custom is False


@pytest.mark.asyncio
async def test_catalog_rate_is_used_without_override(user, currencies, session_maker):
    rates = await CurrencyService.get_rates(base="USD", user_id=user.id, session_maker=session_maker)
    by_code = {rate.code: rate for rate in rates}

    assert by_code["EUR"].rate == pytest.approx(0.909091, rel=1e-4)
    assert by_code["EUR"].is_custom is False


@pytest.mark.asyncio
async def test_user_rates_are_isolated(user, other_user, currencies, session_maker):
    await CurrencyService.set_user_rate(code="EUR", rate=2.0, user_id=user.id, session_maker=session_maker)

    foreign = await CurrencyService.get_rates(base="USD", user_id=other_user.id, session_maker=session_maker)

    assert {rate.code: rate for rate in foreign}["EUR"].is_custom is False


@pytest.mark.asyncio
async def test_rate_can_be_updated(user, currencies, session_maker):
    await CurrencyService.set_user_rate(code="EUR", rate=2.0, user_id=user.id, session_maker=session_maker)
    await CurrencyService.set_user_rate(code="EUR", rate=3.0, user_id=user.id, session_maker=session_maker)

    async with session_maker() as session:
        stored = (
            (await session.execute(select(UserCurrencyRateModel).where(UserCurrencyRateModel.user_id == user.id)))
            .scalars()
            .all()
        )

    assert len(stored) == 1
    # Display 3.0 EUR per USD is stored in catalog semantics: 1 / 3 USD per EUR.
    assert stored[0].rate == pytest.approx(1 / 3)


@pytest.mark.asyncio
async def test_reset_returns_to_catalog_rate(user, currencies, session_maker):
    await CurrencyService.set_user_rate(code="EUR", rate=2.0, user_id=user.id, session_maker=session_maker)
    await CurrencyService.reset_user_rate(code="EUR", user_id=user.id, session_maker=session_maker)

    rates = await CurrencyService.get_rates(base="USD", user_id=user.id, session_maker=session_maker)

    assert {rate.code: rate for rate in rates}["EUR"].is_custom is False


@pytest.mark.asyncio
async def test_rate_endpoints_through_api(verified_user_client, currencies):
    client, _, _ = verified_user_client

    response = await client.put("/api/finance/currencies/EUR/rate", json={"rate": 2.5})
    assert response.status_code == 200
    assert response.json()["code"] == "EUR"
    assert response.json()["rate"] == pytest.approx(2.5)
    assert response.json()["is_custom"] is True

    rates = await client.get("/api/finance/currencies/rates", params={"base": "USD"})
    by_code = {item["code"]: item for item in rates.json()}
    assert by_code["EUR"]["is_custom"] is True
    assert by_code["EUR"]["rate"] == pytest.approx(2.5)

    reset = await client.delete("/api/finance/currencies/EUR/rate")
    assert reset.status_code == 204

    rates = await client.get("/api/finance/currencies/rates", params={"base": "USD"})
    assert {item["code"]: item for item in rates.json()}["EUR"]["is_custom"] is False


@pytest.mark.asyncio
async def test_rate_endpoint_validates_input(verified_user_client, currencies):
    client, _, _ = verified_user_client

    negative = await client.put("/api/finance/currencies/EUR/rate", json={"rate": -1})
    assert negative.status_code == 422

    unknown = await client.put("/api/finance/currencies/XXX/rate", json={"rate": 1.0})
    assert unknown.status_code == 404


@pytest.mark.asyncio
async def test_reset_without_override_returns_404(verified_user_client, currencies):
    client, _, _ = verified_user_client

    response = await client.delete("/api/finance/currencies/EUR/rate")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_rates_endpoint_is_public_without_personal_rates(async_client: AsyncClient, currencies):
    """The currency catalog is not personal data: we return it even without a session."""
    del currencies

    response = await async_client.get("/api/finance/currencies/rates", params={"base": "USD"})

    assert response.status_code == 200
    assert all(item["is_custom"] is False for item in response.json())


@pytest.mark.asyncio
async def test_setting_rate_requires_authentication(async_client: AsyncClient, currencies):
    del currencies

    response = await async_client.put("/api/finance/currencies/EUR/rate", json={"rate": 2.0})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_base_currency_rate_cannot_be_overridden(user, currencies, session_maker):
    async with session_maker() as session:
        db_user = await session.get(UserModel, user.id)
        db_user.base_currency = "USD"
        await session.commit()

    with pytest.raises(HTTPException) as caught:
        await CurrencyService.set_user_rate(code="USD", rate=2.0, user_id=user.id, session_maker=session_maker)
    assert caught.value.status_code == 400


@pytest.mark.asyncio
async def test_display_rate_round_trip_with_non_usd_base(user, currencies, session_maker):
    """Base EUR (catalog 1.1): entering 2 USD per 1 EUR stores 0.55 and reads back 2."""
    async with session_maker() as session:
        db_user = await session.get(UserModel, user.id)
        db_user.base_currency = "EUR"
        await session.commit()

    result = await CurrencyService.set_user_rate(code="USD", rate=2.0, user_id=user.id, session_maker=session_maker)
    assert result.rate == pytest.approx(2.0)

    rates = await CurrencyService.get_rates(user_id=user.id, session_maker=session_maker)
    assert {rate.code: rate for rate in rates}["USD"].rate == pytest.approx(2.0)
