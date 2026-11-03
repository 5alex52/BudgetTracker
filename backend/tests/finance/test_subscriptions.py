import pytest
from fastapi import HTTPException
from src.finance.schemas import SubscriptionCreate
from src.finance.schemas import SubscriptionFrequency
from src.finance.schemas import SubscriptionUpdate
from src.finance.schemas import TransactionCreate
from src.finance.schemas import TransactionType
from src.finance.service import SubscriptionService
from src.finance.service import TransactionService


async def create_expense_transaction(
    session_maker,
    user_id,
    account_id,
    category_id,
    amount=15.99,
    date="2024-05-15T12:00:00",
):
    return await TransactionService.create_for_user(
        schema=TransactionCreate(
            account_id=account_id,
            category_id=category_id,
            amount=amount,
            currency_id="USD",
            type=TransactionType.EXPENSE,
            date=date,
        ),
        user_id=user_id,
        session_maker=session_maker,
    )


@pytest.mark.asyncio
async def test_create_subscription_marks_transaction(
    account, expense_category, user, session_maker
):
    transaction = await create_expense_transaction(
        session_maker, user.id, account.id, expense_category.id
    )

    subscription = await SubscriptionService.create_for_user(
        schema=SubscriptionCreate(
            transaction_id=transaction.id,
            frequency=SubscriptionFrequency.MONTHLY,
            next_payment_date="2024-06-15T12:00:00",
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    assert subscription.id is not None
    assert subscription.transaction_id == transaction.id
    assert subscription.frequency == SubscriptionFrequency.MONTHLY
    assert subscription.is_active is True

    updated_transaction = await TransactionService.get_by_user(
        transaction.id, user.id, session_maker=session_maker
    )
    assert updated_transaction.is_subscription is True


@pytest.mark.asyncio
async def test_duplicate_subscription_is_rejected(
    account, expense_category, user, session_maker
):
    transaction = await create_expense_transaction(
        session_maker, user.id, account.id, expense_category.id
    )
    schema = SubscriptionCreate(
        transaction_id=transaction.id,
        frequency=SubscriptionFrequency.MONTHLY,
        next_payment_date="2024-06-15T12:00:00",
    )
    await SubscriptionService.create_for_user(
        schema=schema, user_id=user.id, session_maker=session_maker
    )

    with pytest.raises(HTTPException) as error:
        await SubscriptionService.create_for_user(
            schema=schema, user_id=user.id, session_maker=session_maker
        )

    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_income_transaction_cannot_be_subscription(
    account, income_category, user, session_maker
):
    transaction = await TransactionService.create_for_user(
        schema=TransactionCreate(
            account_id=account.id,
            category_id=income_category.id,
            amount=100.0,
            currency_id="USD",
            type=TransactionType.INCOME,
            date="2024-05-15T12:00:00",
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    with pytest.raises(HTTPException) as error:
        await SubscriptionService.create_for_user(
            schema=SubscriptionCreate(
                transaction_id=transaction.id,
                frequency=SubscriptionFrequency.MONTHLY,
                next_payment_date="2024-06-15T12:00:00",
            ),
            user_id=user.id,
            session_maker=session_maker,
        )

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_next_payment_date_cannot_be_in_the_past(
    account, expense_category, user, session_maker
):
    transaction = await create_expense_transaction(
        session_maker,
        user.id,
        account.id,
        expense_category.id,
        date="2024-05-15T12:00:00",
    )

    with pytest.raises(HTTPException) as error:
        await SubscriptionService.create_for_user(
            schema=SubscriptionCreate(
                transaction_id=transaction.id,
                frequency=SubscriptionFrequency.MONTHLY,
                next_payment_date="2024-01-01T00:00:00",
            ),
            user_id=user.id,
            session_maker=session_maker,
        )

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_advance_next_payment_date(
    account, expense_category, user, session_maker
):
    transaction = await create_expense_transaction(
        session_maker, user.id, account.id, expense_category.id
    )
    subscription = await SubscriptionService.create_for_user(
        schema=SubscriptionCreate(
            transaction_id=transaction.id,
            frequency=SubscriptionFrequency.MONTHLY,
            next_payment_date="2024-06-15T12:00:00",
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    advanced = await SubscriptionService.advance_next_payment(
        subscription.id, user.id, session_maker=session_maker
    )

    assert advanced.next_payment_date.month == 7
    assert advanced.next_payment_date.day == 15


@pytest.mark.asyncio
async def test_deactivate_and_delete_subscription(
    account, expense_category, user, session_maker
):
    transaction = await create_expense_transaction(
        session_maker, user.id, account.id, expense_category.id
    )
    subscription = await SubscriptionService.create_for_user(
        schema=SubscriptionCreate(
            transaction_id=transaction.id,
            frequency=SubscriptionFrequency.WEEKLY,
            next_payment_date="2024-05-22T12:00:00",
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    paused = await SubscriptionService.update_for_user(
        subscription_id=subscription.id,
        schema=SubscriptionUpdate(is_active=False),
        user_id=user.id,
        session_maker=session_maker,
    )
    assert paused.is_active is False
    assert (
        await SubscriptionService.get_list_by_user(
            user.id, is_active=True, session_maker=session_maker
        )
        == []
    )

    await SubscriptionService.delete_for_user(
        subscription.id, user.id, session_maker=session_maker
    )

    with pytest.raises(HTTPException) as error:
        await SubscriptionService.get_by_user(
            subscription.id, user.id, session_maker=session_maker
        )

    assert error.value.status_code == 404

    updated_transaction = await TransactionService.get_by_user(
        transaction.id, user.id, session_maker=session_maker
    )
    assert updated_transaction.is_subscription is False


@pytest.mark.asyncio
async def test_subscriptions_are_isolated_between_users(
    account, expense_category, other_user, user, session_maker
):
    transaction = await create_expense_transaction(
        session_maker, user.id, account.id, expense_category.id
    )
    subscription = await SubscriptionService.create_for_user(
        schema=SubscriptionCreate(
            transaction_id=transaction.id,
            frequency=SubscriptionFrequency.MONTHLY,
            next_payment_date="2024-06-15T12:00:00",
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    with pytest.raises(HTTPException) as error:
        await SubscriptionService.get_by_user(
            subscription.id, other_user.id, session_maker=session_maker
        )

    assert error.value.status_code == 404
