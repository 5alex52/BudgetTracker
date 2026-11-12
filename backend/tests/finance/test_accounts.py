from datetime import datetime

import pytest
from fastapi import HTTPException
from src.finance.schemas import AccountCreate
from src.finance.schemas import AccountType
from src.finance.schemas import AccountUpdate
from src.finance.service import AccountService
from src.finance.service import CurrencyService


@pytest.mark.asyncio
async def test_create_account(user, currencies, session_maker):
    account = await AccountService.create_for_user(
        schema=AccountCreate(name="Wallet", type=AccountType.CASH, currency_id="USD", balance=100.0),
        user_id=user.id,
        session_maker=session_maker,
    )

    assert account.id is not None
    assert account.name == "Wallet"
    assert account.type == AccountType.CASH
    assert account.currency_id == "USD"
    assert account.balance == 100.0
    assert account.is_archived is False
    assert account.user_id == user.id


@pytest.mark.asyncio
async def test_create_account_with_unknown_currency(user, currencies, session_maker):
    with pytest.raises(HTTPException) as error:
        await AccountService.create_for_user(
            schema=AccountCreate(name="Wallet", type=AccountType.CASH, currency_id="GBP"),
            user_id=user.id,
            session_maker=session_maker,
        )

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_get_account_by_user(account, user, session_maker):
    retrieved = await AccountService.get_by_user(account.id, user.id, session_maker=session_maker)

    assert retrieved.id == account.id
    assert retrieved.name == account.name


@pytest.mark.asyncio
async def test_accounts_are_isolated_between_users(account, other_user, session_maker):
    with pytest.raises(HTTPException) as error:
        await AccountService.get_by_user(account.id, other_user.id, session_maker=session_maker)

    assert error.value.status_code == 404
    assert await AccountService.get_list_by_user(other_user.id, session_maker=session_maker) == []


@pytest.mark.asyncio
async def test_update_account(account, user, session_maker):
    updated = await AccountService.update_for_user(
        account_id=account.id,
        schema=AccountUpdate(name="Main cash", balance=250.5),
        user_id=user.id,
        session_maker=session_maker,
    )

    assert updated.name == "Main cash"
    assert updated.balance == 250.5
    assert updated.currency_id == account.currency_id


@pytest.mark.asyncio
async def test_archive_account_hides_it_from_the_list(account, user, session_maker):
    await AccountService.set_archived(account.id, user.id, True, session_maker=session_maker)

    assert await AccountService.get_list_by_user(user.id, session_maker=session_maker) == []

    archived = await AccountService.get_list_by_user(user.id, include_archived=True, session_maker=session_maker)
    assert len(archived) == 1
    assert archived[0].is_archived is True


@pytest.mark.asyncio
async def test_delete_account(account, user, session_maker):
    await AccountService.delete_for_user(account.id, user.id, session_maker=session_maker)

    with pytest.raises(HTTPException) as error:
        await AccountService.get_by_user(account.id, user.id, session_maker=session_maker)

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_balance_overview_uses_base_currency(user, currencies, session_maker):
    await AccountService.create_for_user(
        schema=AccountCreate(
            name="USD account",
            type=AccountType.CHECKING,
            currency_id="USD",
            balance=1000.0,
        ),
        user_id=user.id,
        session_maker=session_maker,
    )
    await AccountService.create_for_user(
        schema=AccountCreate(
            name="EUR account",
            type=AccountType.CHECKING,
            currency_id="EUR",
            balance=100.0,
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    overview = await AccountService.get_balance_overview(user.id, session_maker=session_maker)

    assert overview.total == 1110.0
    assert len(overview.accounts) == 2
    assert {item.currency_id for item in overview.accounts} == {"USD", "EUR"}


@pytest.mark.asyncio
async def test_balance_overview_uses_personal_currency_rate(user, currencies, session_maker):
    """Personal rate 0.5 EUR per 1 USD (1 EUR = 2 USD) gives 200 USD for a 100 EUR account."""
    await CurrencyService.set_user_rate(code="EUR", rate=0.5, user_id=user.id, session_maker=session_maker)
    await AccountService.create_for_user(
        schema=AccountCreate(
            name="EUR account",
            type=AccountType.CHECKING,
            currency_id="EUR",
            balance=100.0,
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    overview = await AccountService.get_balance_overview(user.id, session_maker=session_maker)

    assert overview.total == 200.0
    assert overview.accounts[0].balance == 100.0
    assert overview.accounts[0].balance_base == 200.0
