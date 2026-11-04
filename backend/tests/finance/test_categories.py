import pytest
from fastapi import HTTPException
from src.finance.schemas import CategoryCreate
from src.finance.schemas import CategoryType
from src.finance.schemas import CategoryUpdate
from src.finance.schemas import TransactionCreate
from src.finance.schemas import TransactionType
from src.finance.service import CategoryService
from src.finance.service import TransactionService


@pytest.mark.asyncio
async def test_create_category(user, session_maker):
    category = await CategoryService.create_for_user(
        schema=CategoryCreate(name="Groceries", type=CategoryType.EXPENSE, icon="cart", color="#ff0000"),
        user_id=user.id,
        session_maker=session_maker,
    )

    assert category.id is not None
    assert category.name == "Groceries"
    assert category.type == CategoryType.EXPENSE
    assert category.icon == "cart"
    assert category.color == "#ff0000"
    assert category.user_id == user.id


@pytest.mark.asyncio
async def test_list_categories_filtered_by_type(user, expense_category, income_category, session_maker):
    expenses = await CategoryService.get_list_by_user(
        user.id, category_type=CategoryType.EXPENSE, session_maker=session_maker
    )
    incomes = await CategoryService.get_list_by_user(
        user.id, category_type=CategoryType.INCOME, session_maker=session_maker
    )

    # On registration the service creates a set of default categories, so
    # we check the type filter rather than the exact list.
    assert expense_category.id in [category.id for category in expenses]
    assert income_category.id in [category.id for category in incomes]
    assert all(category.type == CategoryType.EXPENSE for category in expenses)
    assert all(category.type == CategoryType.INCOME for category in incomes)


@pytest.mark.asyncio
async def test_subcategory_must_share_parent_type(user, expense_category, session_maker):
    child = await CategoryService.create_for_user(
        schema=CategoryCreate(name="Vegetables", type=CategoryType.EXPENSE, parent_id=expense_category.id),
        user_id=user.id,
        session_maker=session_maker,
    )

    assert child.parent_id == expense_category.id

    with pytest.raises(HTTPException) as error:
        await CategoryService.create_for_user(
            schema=CategoryCreate(name="Bonus", type=CategoryType.INCOME, parent_id=expense_category.id),
            user_id=user.id,
            session_maker=session_maker,
        )

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_category_cannot_be_its_own_parent(user, expense_category, session_maker):
    with pytest.raises(HTTPException) as error:
        await CategoryService.update_for_user(
            category_id=expense_category.id,
            schema=CategoryUpdate(parent_id=expense_category.id),
            user_id=user.id,
            session_maker=session_maker,
        )

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_category_with_children_is_forbidden(user, expense_category, session_maker):
    await CategoryService.create_for_user(
        schema=CategoryCreate(name="Vegetables", type=CategoryType.EXPENSE, parent_id=expense_category.id),
        user_id=user.id,
        session_maker=session_maker,
    )

    with pytest.raises(HTTPException) as error:
        await CategoryService.delete_for_user(expense_category.id, user.id, session_maker=session_maker)

    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_delete_category_used_by_transaction_is_forbidden(account, expense_category, user, session_maker):
    await TransactionService.create_for_user(
        schema=TransactionCreate(
            account_id=account.id,
            category_id=expense_category.id,
            amount=10.0,
            currency_id="USD",
            type=TransactionType.EXPENSE,
            date="2024-05-01T12:00:00",
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    with pytest.raises(HTTPException) as error:
        await CategoryService.delete_for_user(expense_category.id, user.id, session_maker=session_maker)

    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_delete_empty_category(user, session_maker):
    category = await CategoryService.create_for_user(
        schema=CategoryCreate(name="Unused", type=CategoryType.EXPENSE),
        user_id=user.id,
        session_maker=session_maker,
    )

    await CategoryService.delete_for_user(category.id, user.id, session_maker=session_maker)

    with pytest.raises(HTTPException) as error:
        await CategoryService.get_by_user(category.id, user.id, session_maker=session_maker)

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_categories_are_isolated_between_users(expense_category, other_user, session_maker):
    with pytest.raises(HTTPException) as error:
        await CategoryService.get_by_user(expense_category.id, other_user.id, session_maker=session_maker)

    assert error.value.status_code == 404
