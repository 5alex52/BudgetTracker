"""Тесты личных курсов валют."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from src.finance.models import UserCurrencyRateModel
from src.finance.service import CurrencyService


@pytest.mark.asyncio
async def test_user_rate_overrides_catalog_rate(user, currencies, session_maker):
    await CurrencyService.set_user_rate(
        code="EUR", rate=2.0, user_id=user.id, session_maker=session_maker
    )

    rates = await CurrencyService.get_rates(
        base="USD", user_id=user.id, session_maker=session_maker
    )
    by_code = {rate.code: rate for rate in rates}

    # 1 USD = 1 / 2.0 EUR вместо справочных 1 / 1.1
    assert by_code["EUR"].rate == pytest.approx(0.5)
    assert by_code["EUR"].is_custom is True
    assert by_code["USD"].is_custom is False


@pytest.mark.asyncio
async def test_catalog_rate_is_used_without_override(user, currencies, session_maker):
    rates = await CurrencyService.get_rates(
        base="USD", user_id=user.id, session_maker=session_maker
    )
    by_code = {rate.code: rate for rate in rates}

    assert by_code["EUR"].rate == pytest.approx(0.909091, rel=1e-4)
    assert by_code["EUR"].is_custom is False


@pytest.mark.asyncio
async def test_user_rates_are_isolated(user, other_user, currencies, session_maker):
    await CurrencyService.set_user_rate(
        code="EUR", rate=2.0, user_id=user.id, session_maker=session_maker
    )

    foreign = await CurrencyService.get_rates(
        base="USD", user_id=other_user.id, session_maker=session_maker
    )

    assert {rate.code: rate for rate in foreign}["EUR"].is_custom is False


@pytest.mark.asyncio
async def test_rate_can_be_updated(user, currencies, session_maker):
    await CurrencyService.set_user_rate(
        code="EUR", rate=2.0, user_id=user.id, session_maker=session_maker
    )
    await CurrencyService.set_user_rate(
        code="EUR", rate=3.0, user_id=user.id, session_maker=session_maker
    )

    async with session_maker() as session:
        stored = (
            (
                await session.execute(
                    select(UserCurrencyRateModel).where(
                        UserCurrencyRateModel.user_id == user.id
                    )
                )
            )
            .scalars()
            .all()
        )

    assert len(stored) == 1
    assert stored[0].rate == 3.0


@pytest.mark.asyncio
async def test_reset_returns_to_catalog_rate(user, currencies, session_maker):
    await CurrencyService.set_user_rate(
        code="EUR", rate=2.0, user_id=user.id, session_maker=session_maker
    )
    await CurrencyService.reset_user_rate(
        code="EUR", user_id=user.id, session_maker=session_maker
    )

    rates = await CurrencyService.get_rates(
        base="USD", user_id=user.id, session_maker=session_maker
    )

    assert {rate.code: rate for rate in rates}["EUR"].is_custom is False


@pytest.mark.asyncio
async def test_rate_endpoints_through_api(verified_user_client, currencies):
    client, _, _ = verified_user_client

    response = await client.put("/api/finance/currencies/EUR/rate", json={"rate": 2.5})
    assert response.status_code == 200
    assert response.json()["code"] == "EUR"
    assert response.json()["is_custom"] is True

    rates = await client.get("/api/finance/currencies/rates", params={"base": "USD"})
    by_code = {item["code"]: item for item in rates.json()}
    assert by_code["EUR"]["is_custom"] is True
    assert by_code["EUR"]["rate"] == pytest.approx(0.4)

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
async def test_rates_endpoint_is_public_without_personal_rates(
    async_client: AsyncClient, currencies
):
    """Справочник курсов не является личными данными: без сессии отдаём его же."""
    del currencies

    response = await async_client.get(
        "/api/finance/currencies/rates", params={"base": "USD"}
    )

    assert response.status_code == 200
    assert all(item["is_custom"] is False for item in response.json())


@pytest.mark.asyncio
async def test_setting_rate_requires_authentication(
    async_client: AsyncClient, currencies
):
    del currencies

    response = await async_client.put(
        "/api/finance/currencies/EUR/rate", json={"rate": 2.0}
    )

    assert response.status_code == 401
