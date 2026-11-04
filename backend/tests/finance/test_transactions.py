import pytest
from fastapi import HTTPException
from src.finance.schemas import AccountCreate
from src.finance.schemas import AccountType
from src.finance.schemas import CategoryCreate
from src.finance.schemas import CategoryType
from src.finance.schemas import TransactionCreate
from src.finance.schemas import TransactionType
from src.finance.schemas import TransactionUpdate
from src.finance.service import AccountService
from src.finance.service import CategoryService
from src.finance.service import TransactionService


async def create_transaction(session_maker, user_id, **overrides):
    payload = {
        "account_id": overrides.pop("account_id"),
        "category_id": overrides.pop("category_id"),
        "amount": 100.0,
        "currency_id": "USD",
        "type": TransactionType.EXPENSE,
        "date": "2024-05-15T12:00:00",
    }
    payload.update(overrides)
    return await TransactionService.create_for_user(
        schema=TransactionCreate(**payload),
        user_id=user_id,
        session_maker=session_maker,
    )


@pytest.mark.asyncio
async def test_expense_decreases_account_balance(account, expense_category, user, session_maker):
    transaction = await create_transaction(
        session_maker,
        user.id,
        account_id=account.id,
        category_id=expense_category.id,
        amount=150.0,
    )

    assert transaction.id is not None
    assert transaction.amount == 150.0
    assert transaction.type == TransactionType.EXPENSE

    refreshed = await AccountService.get_by_user(account.id, user.id, session_maker=session_maker)
    assert refreshed.balance == 850.0


@pytest.mark.asyncio
async def test_income_increases_account_balance(account, income_category, user, session_maker):
    await create_transaction(
        session_maker,
        user.id,
        account_id=account.id,
        category_id=income_category.id,
        amount=200.0,
        type=TransactionType.INCOME,
    )

    refreshed = await AccountService.get_by_user(account.id, user.id, session_maker=session_maker)
    assert refreshed.balance == 1200.0


@pytest.mark.asyncio
async def test_transaction_in_foreign_currency_is_converted(
    account, expense_category, user, session_maker, premium_entitlements
):
    await create_transaction(
        session_maker,
        user.id,
        account_id=account.id,
        category_id=expense_category.id,
        amount=100.0,
        currency_id="EUR",
    )

    refreshed = await AccountService.get_by_user(account.id, user.id, session_maker=session_maker)
    # 100 EUR * 1.1 (rate to base) / 1.0 (account currency rate)
    assert refreshed.balance == 890.0


@pytest.mark.asyncio
async def test_category_type_must_match_transaction_type(account, income_category, user, session_maker):
    with pytest.raises(HTTPException) as error:
        await create_transaction(
            session_maker,
            user.id,
            account_id=account.id,
            category_id=income_category.id,
            amount=10.0,
            type=TransactionType.EXPENSE,
        )

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_transaction_of_foreign_account_is_not_found(
    account, expense_category, other_user, currencies, session_maker
):
    foreign_account = await AccountService.create_for_user(
        schema=AccountCreate(name="Foreign", type=AccountType.CASH, currency_id="USD"),
        user_id=other_user.id,
        session_maker=session_maker,
    )

    with pytest.raises(HTTPException) as error:
        await create_transaction(
            session_maker,
            other_user.id,
            account_id=foreign_account.id,
            category_id=expense_category.id,
            amount=10.0,
        )

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_update_transaction_recalculates_balance(account, expense_category, user, session_maker):
    transaction = await create_transaction(
        session_maker,
        user.id,
        account_id=account.id,
        category_id=expense_category.id,
        amount=150.0,
    )

    await TransactionService.update_for_user(
        transaction_id=transaction.id,
        schema=TransactionUpdate(amount=50.0),
        user_id=user.id,
        session_maker=session_maker,
    )

    refreshed = await AccountService.get_by_user(account.id, user.id, session_maker=session_maker)
    assert refreshed.balance == 950.0


@pytest.mark.asyncio
async def test_update_transaction_moves_money_between_accounts(
    account, second_account, expense_category, user, session_maker
):
    transaction = await create_transaction(
        session_maker,
        user.id,
        account_id=account.id,
        category_id=expense_category.id,
        amount=100.0,
    )

    await TransactionService.update_for_user(
        transaction_id=transaction.id,
        schema=TransactionUpdate(account_id=second_account.id),
        user_id=user.id,
        session_maker=session_maker,
    )

    source = await AccountService.get_by_user(account.id, user.id, session_maker=session_maker)
    target = await AccountService.get_by_user(second_account.id, user.id, session_maker=session_maker)

    assert source.balance == 1000.0
    assert target.balance == 400.0


@pytest.mark.asyncio
async def test_delete_transaction_restores_balance(account, expense_category, user, session_maker):
    transaction = await create_transaction(
        session_maker,
        user.id,
        account_id=account.id,
        category_id=expense_category.id,
        amount=150.0,
    )

    await TransactionService.delete_for_user(transaction.id, user.id, session_maker=session_maker)

    refreshed = await AccountService.get_by_user(account.id, user.id, session_maker=session_maker)
    assert refreshed.balance == 1000.0

    with pytest.raises(HTTPException) as error:
        await TransactionService.get_by_user(transaction.id, user.id, session_maker=session_maker)

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_list_transactions_with_filters(account, expense_category, income_category, user, session_maker):
    await create_transaction(
        session_maker,
        user.id,
        account_id=account.id,
        category_id=expense_category.id,
        amount=10.0,
    )
    await create_transaction(
        session_maker,
        user.id,
        account_id=account.id,
        category_id=income_category.id,
        amount=500.0,
        type=TransactionType.INCOME,
        date="2024-06-10T09:00:00",
    )

    expenses = await TransactionService.get_list_by_user(
        user.id, transaction_type=TransactionType.EXPENSE, session_maker=session_maker
    )
    summer = await TransactionService.get_list_by_user(
        user.id,
        start_date="2024-06-01T00:00:00",
        end_date="2024-06-30T23:59:59",
        session_maker=session_maker,
    )

    assert len(expenses) == 1
    assert expenses[0].type == TransactionType.EXPENSE
    assert len(summer) == 1
    assert summer[0].amount == 500.0


@pytest.mark.asyncio
async def test_invalid_period_is_rejected(account, user, session_maker):
    with pytest.raises(HTTPException) as error:
        await TransactionService.get_list_by_user(
            user.id,
            start_date="2024-06-30T00:00:00",
            end_date="2024-06-01T00:00:00",
            session_maker=session_maker,
        )

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_summary_groups_by_category(account, expense_category, user, session_maker):
    second_category = await CategoryService.create_for_user(
        schema=CategoryCreate(name="Restaurants", type=CategoryType.EXPENSE),
        user_id=user.id,
        session_maker=session_maker,
    )

    await create_transaction(
        session_maker,
        user.id,
        account_id=account.id,
        category_id=expense_category.id,
        amount=100.0,
    )
    await create_transaction(
        session_maker,
        user.id,
        account_id=account.id,
        category_id=expense_category.id,
        amount=50.0,
    )
    await create_transaction(
        session_maker,
        user.id,
        account_id=account.id,
        category_id=second_category.id,
        amount=25.0,
    )

    summary = await TransactionService.get_summary(
        user.id, transaction_type=TransactionType.EXPENSE, session_maker=session_maker
    )

    assert summary.total == 175.0
    assert summary.transactions_count == 3
    assert len(summary.by_category) == 2
    assert summary.by_category[0].name == "Groceries"
    assert summary.by_category[0].total == 150.0
    assert summary.by_category[0].transactions_count == 2


@pytest.mark.asyncio
async def test_transfer_moves_money_to_second_account(account, second_account, user, session_maker):
    transfer = await create_transaction(
        session_maker,
        user.id,
        account_id=account.id,
        category_id=None,
        amount=100.0,
        type=TransactionType.TRANSFER,
        transfer_account_id=second_account.id,
    )

    assert transfer.transfer_account_id == second_account.id
    # A transfer does not require a category: the server creates a system one
    assert transfer.category.type == CategoryType.TRANSFER

    source = await AccountService.get_by_user(account.id, user.id, session_maker=session_maker)
    target = await AccountService.get_by_user(second_account.id, user.id, session_maker=session_maker)
    assert source.balance == 900.0
    assert target.balance == 600.0

    await TransactionService.delete_for_user(transfer.id, user.id, session_maker=session_maker)

    source = await AccountService.get_by_user(account.id, user.id, session_maker=session_maker)
    target = await AccountService.get_by_user(second_account.id, user.id, session_maker=session_maker)
    assert source.balance == 1000.0
    assert target.balance == 500.0


@pytest.mark.asyncio
async def test_update_transfer_amount_moves_both_balances(account, second_account, user, session_maker):
    transfer = await create_transaction(
        session_maker,
        user.id,
        account_id=account.id,
        category_id=None,
        amount=100.0,
        type=TransactionType.TRANSFER,
        transfer_account_id=second_account.id,
    )

    await TransactionService.update_for_user(
        transaction_id=transfer.id,
        schema=TransactionUpdate(amount=40.0),
        user_id=user.id,
        session_maker=session_maker,
    )

    source = await AccountService.get_by_user(account.id, user.id, session_maker=session_maker)
    target = await AccountService.get_by_user(second_account.id, user.id, session_maker=session_maker)
    assert source.balance == 960.0
    assert target.balance == 540.0


@pytest.mark.asyncio
async def test_transfer_requires_distinct_account(account, user, session_maker):
    with pytest.raises(HTTPException) as error:
        await create_transaction(
            session_maker,
            user.id,
            account_id=account.id,
            category_id=None,
            amount=10.0,
            type=TransactionType.TRANSFER,
            transfer_account_id=account.id,
        )

    assert error.value.status_code == 400
