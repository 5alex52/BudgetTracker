from datetime import datetime

import pytest
from fastapi import HTTPException
from src.finance.dao import AccountDAO
from src.finance.schemas import AccountCreate
from src.finance.schemas import AccountType
from src.finance.schemas import AccountUpdate
from src.finance.schemas import TransactionCreate
from src.finance.schemas import TransactionType
from src.finance.service import AccountService
from src.finance.service import CurrencyService
from src.finance.service import TransactionService


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
async def test_balance_overview_uses_base_currency(user, currencies, session_maker, premium_entitlements):
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
    assert all(item.is_locked is False for item in overview.accounts)


@pytest.mark.asyncio
async def test_balance_overview_uses_personal_currency_rate(user, currencies, session_maker, premium_entitlements):
    """Personal rate 1 EUR = 2 USD gives 200 USD for an account with 100 EUR balance."""
    await CurrencyService.set_user_rate(code="EUR", rate=2.0, user_id=user.id, session_maker=session_maker)
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


@pytest.mark.asyncio
async def test_free_plan_blocks_third_account(user, account, second_account, currencies, session_maker):
    """Free plan: two accounts is the maximum you can create."""
    with pytest.raises(HTTPException) as error:
        await AccountService.create_for_user(
            schema=AccountCreate(name="Third", type=AccountType.CASH, currency_id="USD", balance=0.0),
            user_id=user.id,
            session_maker=session_maker,
        )

    assert error.value.status_code == 402
    assert "limit" in error.value.detail.lower()


@pytest.mark.asyncio
async def test_free_plan_limit_counts_locked_legacy_accounts(user, account, currencies, session_maker):
    """A locked account of a different currency still counts against the limit."""
    async with session_maker() as session:
        await AccountDAO.create(
            session,
            {
                "user_id": user.id,
                "name": "Legacy EUR",
                "type": AccountType.CASH,
                "currency_id": "EUR",
                "balance": 100.0,
            },
        )
        await session.commit()

    with pytest.raises(HTTPException) as error:
        await AccountService.create_for_user(
            schema=AccountCreate(name="Second USD", type=AccountType.CASH, currency_id="USD", balance=0.0),
            user_id=user.id,
            session_maker=session_maker,
        )

    assert error.value.status_code == 402
    assert "limit" in error.value.detail.lower()


@pytest.mark.asyncio
async def test_free_plan_blocks_foreign_currency_account(user, currencies, session_maker):
    with pytest.raises(HTTPException) as error:
        await AccountService.create_for_user(
            schema=AccountCreate(name="Euro", type=AccountType.CASH, currency_id="EUR", balance=0.0),
            user_id=user.id,
            session_maker=session_maker,
        )

    assert error.value.status_code == 402
    assert "base currency" in error.value.detail.lower()


@pytest.mark.asyncio
async def test_existing_accounts_are_marked_read_only(user, account, second_account, currencies, session_maker):
    """Accounts over the limit and in a foreign currency remain but are locked."""
    async with session_maker() as session:
        third = await AccountDAO.create(
            session,
            {
                "user_id": user.id,
                "name": "Third",
                "type": AccountType.CASH,
                "currency_id": "USD",
                "balance": 0.0,
            },
        )
        await AccountDAO.create(
            session,
            {
                "user_id": user.id,
                "name": "Euro",
                "type": AccountType.CASH,
                "currency_id": "EUR",
                "balance": 100.0,
            },
        )
        await session.commit()
        third_id = third.id

    accounts = await AccountService.get_list_by_user(user.id, session_maker=session_maker)
    by_id = {item.id: item for item in accounts}

    assert by_id[account.id].is_locked is False
    assert by_id[second_account.id].is_locked is False
    assert by_id[third_id].is_locked is True
    assert by_id[third_id].lock_reason == "subscription_required_account_limit"
    euro = next(item for item in accounts if item.currency_id == "EUR")
    assert euro.is_locked is True
    assert euro.lock_reason == "subscription_required_currency"

    with pytest.raises(HTTPException) as error:
        await AccountService.update_for_user(
            third_id,
            AccountUpdate(name="Renamed"),
            user_id=user.id,
            session_maker=session_maker,
        )
    assert error.value.status_code == 402


@pytest.mark.asyncio
async def test_transaction_on_locked_account_is_rejected(
    user,
    account,
    second_account,
    expense_category,
    currencies,
    session_maker,
):
    async with session_maker() as session:
        third = await AccountDAO.create(
            session,
            {
                "user_id": user.id,
                "name": "Third",
                "type": AccountType.CASH,
                "currency_id": "USD",
                "balance": 0.0,
            },
        )
        await session.commit()
        third_id = third.id

    with pytest.raises(HTTPException) as error:
        await TransactionService.create_for_user(
            TransactionCreate(
                account_id=third_id,
                category_id=expense_category.id,
                amount=10.0,
                currency_id="USD",
                type=TransactionType.EXPENSE,
                date=datetime.now(),
            ),
            user_id=user.id,
            session_maker=session_maker,
        )

    assert error.value.status_code == 402
