import pytest
from fastapi import HTTPException
from src.finance.schemas import AccountCreate
from src.finance.schemas import AccountType
from src.finance.schemas import CurrencyCreate
from src.finance.schemas import CurrencyUpdate
from src.finance.service import AccountService
from src.finance.service import CurrencyService


@pytest.mark.asyncio
async def test_currency_crud(session_maker):
    created = await CurrencyService.create(
        schema=CurrencyCreate(code="BYN", name="Belarusian Ruble", symbol="Br", exchange_rate_to_base=0.3),
        session_maker=session_maker,
    )
    assert created.code == "BYN"
    assert created.exchange_rate_to_base == 0.3

    currencies = await CurrencyService.get_list(session_maker=session_maker)
    assert "BYN" in [currency.code for currency in currencies]

    updated = await CurrencyService.update(
        code="BYN",
        schema=CurrencyUpdate(exchange_rate_to_base=0.31),
        session_maker=session_maker,
    )
    assert updated.exchange_rate_to_base == 0.31

    await CurrencyService.delete("BYN", session_maker=session_maker)

    with pytest.raises(HTTPException) as error:
        await CurrencyService.get("BYN", session_maker=session_maker)

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_currency_used_by_account_cannot_be_deleted(user, account, session_maker):
    with pytest.raises(HTTPException) as error:
        await CurrencyService.delete("USD", session_maker=session_maker)

    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_account_cannot_use_unknown_currency(user, session_maker):
    with pytest.raises(HTTPException) as error:
        await AccountService.create_for_user(
            schema=AccountCreate(name="Wallet", type=AccountType.CASH, currency_id="XXX"),
            user_id=user.id,
            session_maker=session_maker,
        )

    assert error.value.status_code == 400
