"""Тесты «Записей», «Категорий», «Счетов» и «Валют»: выборки и агрегаты."""

from datetime import datetime

import pytest
from fastapi import HTTPException
from src.finance.schemas import AccountCreate
from src.finance.schemas import AccountType
from src.finance.schemas import CategoryCreate
from src.finance.schemas import CategoryType
from src.finance.schemas import TransactionCreate
from src.finance.schemas import TransactionType
from src.finance.service import AccountService
from src.finance.service import CategoryService
from src.finance.service import CurrencyService
from src.finance.service import TransactionService

PERIOD_START = datetime(2025, 10, 1)
PERIOD_END = datetime(2025, 10, 31, 23, 59, 59)


async def _tx(
    account, category, user, session_maker, amount, transaction_type, when, note=""
):
    return await TransactionService.create_for_user(
        schema=TransactionCreate(
            account_id=account.id,
            category_id=category.id,
            amount=amount,
            currency_id=account.currency_id,
            type=transaction_type,
            date=when,
            note=note,
        ),
        user_id=user.id,
        session_maker=session_maker,
    )


# --------------------------------------------------------------------------- #
#  Счета
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_account_summary_reports_turnover(
    user, account, expense_category, income_category, session_maker
):
    await _tx(
        account,
        income_category,
        user,
        session_maker,
        400.0,
        TransactionType.INCOME,
        PERIOD_START,
    )
    await _tx(
        account,
        expense_category,
        user,
        session_maker,
        150.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )

    summary = await AccountService.get_summary(
        account_id=account.id,
        user_id=user.id,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        session_maker=session_maker,
    )

    assert summary.income == 400.0
    assert summary.expense == 150.0
    assert summary.net == 250.0
    assert summary.transactions_count == 2
    assert summary.balance == 1250.0


@pytest.mark.asyncio
async def test_account_summary_is_isolated_between_users(
    user, other_user, account, expense_category, session_maker
):
    await _tx(
        account,
        expense_category,
        user,
        session_maker,
        10.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )

    with pytest.raises(HTTPException) as error:
        await AccountService.get_summary(
            account_id=account.id, user_id=other_user.id, session_maker=session_maker
        )

    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_set_excluded_toggles_flag(user, account, session_maker):
    excluded = await AccountService.set_excluded(
        account_id=account.id,
        user_id=user.id,
        is_excluded=True,
        session_maker=session_maker,
    )
    assert excluded.is_excluded is True

    returned = await AccountService.set_excluded(
        account_id=account.id,
        user_id=user.id,
        is_excluded=False,
        session_maker=session_maker,
    )
    assert returned.is_excluded is False


@pytest.mark.asyncio
async def test_list_accounts_can_skip_excluded(
    user, account, second_account, session_maker
):
    await AccountService.set_excluded(
        account_id=second_account.id,
        user_id=user.id,
        is_excluded=True,
        session_maker=session_maker,
    )

    with_excluded = await AccountService.get_list_by_user(
        user.id, session_maker=session_maker
    )
    without_excluded = await AccountService.get_list_by_user(
        user.id, include_excluded=False, session_maker=session_maker
    )

    assert len(with_excluded) == 2
    assert [item.id for item in without_excluded] == [account.id]


# --------------------------------------------------------------------------- #
#  Категории
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_category_tree_has_children_and_counts(
    user, account, expense_category, session_maker
):
    child = await CategoryService.create_for_user(
        schema=CategoryCreate(
            name="Groceries", type=CategoryType.EXPENSE, parent_id=expense_category.id
        ),
        user_id=user.id,
        session_maker=session_maker,
    )
    await _tx(
        account, child, user, session_maker, 20.0, TransactionType.EXPENSE, PERIOD_START
    )
    await _tx(
        account,
        expense_category,
        user,
        session_maker,
        30.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )

    tree = await CategoryService.get_tree(user_id=user.id, session_maker=session_maker)

    root = next(node for node in tree if node.id == expense_category.id)
    assert root.transactions_count == 1
    assert [node.id for node in root.children] == [child.id]
    assert root.children[0].transactions_count == 1


@pytest.mark.asyncio
async def test_category_stats_totals_per_category(
    user, account, expense_category, session_maker
):
    await _tx(
        account,
        expense_category,
        user,
        session_maker,
        45.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )
    await _tx(
        account,
        expense_category,
        user,
        session_maker,
        55.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )

    stats = await CategoryService.get_stats(
        user_id=user.id,
        category_type=CategoryType.EXPENSE,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        session_maker=session_maker,
    )

    assert len(stats) == 1
    assert stats[0].category_id == expense_category.id
    assert stats[0].transactions_count == 2
    assert stats[0].total == 100.0
    assert stats[0].type == CategoryType.EXPENSE


# --------------------------------------------------------------------------- #
#  Записи: фильтры, сортировка, счетчик, массовое удаление
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_list_filters_by_multiple_accounts(
    user, account, second_account, expense_category, session_maker
):
    await _tx(
        account,
        expense_category,
        user,
        session_maker,
        10.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )
    await _tx(
        second_account,
        expense_category,
        user,
        session_maker,
        20.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )

    only_second = await TransactionService.get_list_by_user(
        user.id, session_maker=session_maker, account_ids=[second_account.id]
    )
    both = await TransactionService.get_list_by_user(
        user.id,
        session_maker=session_maker,
        account_ids=[account.id, second_account.id],
    )

    assert len(only_second) == 1
    assert only_second[0].account_id == second_account.id
    assert len(both) == 2


@pytest.mark.asyncio
async def test_list_filters_by_types_and_currency(
    user, account, expense_category, income_category, session_maker
):
    await _tx(
        account,
        income_category,
        user,
        session_maker,
        100.0,
        TransactionType.INCOME,
        PERIOD_START,
    )
    await _tx(
        account,
        expense_category,
        user,
        session_maker,
        40.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )

    incomes = await TransactionService.get_list_by_user(
        user.id, session_maker=session_maker, transaction_types=[TransactionType.INCOME]
    )
    by_currency = await TransactionService.get_list_by_user(
        user.id, session_maker=session_maker, currency_ids=["USD"]
    )
    by_other_currency = await TransactionService.get_list_by_user(
        user.id, session_maker=session_maker, currency_ids=["EUR"]
    )

    assert len(incomes) == 1
    assert incomes[0].type == TransactionType.INCOME
    assert len(by_currency) == 2
    assert by_other_currency == []


@pytest.mark.asyncio
async def test_list_searches_by_note(user, account, expense_category, session_maker):
    await _tx(
        account,
        expense_category,
        user,
        session_maker,
        10.0,
        TransactionType.EXPENSE,
        PERIOD_START,
        "pyaterochka",
    )
    await _tx(
        account,
        expense_category,
        user,
        session_maker,
        20.0,
        TransactionType.EXPENSE,
        PERIOD_START,
        "taxi",
    )

    found = await TransactionService.get_list_by_user(
        user.id, session_maker=session_maker, query="PYATERO"
    )

    assert len(found) == 1
    assert found[0].note == "pyaterochka"


@pytest.mark.asyncio
async def test_list_filters_by_amount_range(
    user, account, expense_category, session_maker
):
    await _tx(
        account,
        expense_category,
        user,
        session_maker,
        10.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )
    await _tx(
        account,
        expense_category,
        user,
        session_maker,
        500.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )

    big = await TransactionService.get_list_by_user(
        user.id, session_maker=session_maker, amount_min=100.0
    )
    small = await TransactionService.get_list_by_user(
        user.id, session_maker=session_maker, amount_max=100.0
    )

    assert [item.amount for item in big] == [500.0]
    assert [item.amount for item in small] == [10.0]


@pytest.mark.asyncio
async def test_list_sorts_by_amount(user, account, expense_category, session_maker):
    await _tx(
        account,
        expense_category,
        user,
        session_maker,
        10.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )
    await _tx(
        account,
        expense_category,
        user,
        session_maker,
        500.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )

    descending = await TransactionService.get_list_by_user(
        user.id, session_maker=session_maker, sort="amount_desc"
    )
    ascending = await TransactionService.get_list_by_user(
        user.id, session_maker=session_maker, sort="amount_asc"
    )

    assert [item.amount for item in descending] == [500.0, 10.0]
    assert [item.amount for item in ascending] == [10.0, 500.0]


@pytest.mark.asyncio
async def test_count_respects_filters(
    user, account, expense_category, income_category, session_maker
):
    await _tx(
        account,
        income_category,
        user,
        session_maker,
        100.0,
        TransactionType.INCOME,
        PERIOD_START,
    )
    await _tx(
        account,
        expense_category,
        user,
        session_maker,
        40.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )

    total = await TransactionService.count_by_user(user.id, session_maker=session_maker)
    expenses = await TransactionService.count_by_user(
        user.id,
        session_maker=session_maker,
        transaction_types=[TransactionType.EXPENSE],
    )

    assert total == 2
    assert expenses == 1


@pytest.mark.asyncio
async def test_bulk_delete_rolls_back_balances(
    user, account, expense_category, session_maker
):
    first = await _tx(
        account,
        expense_category,
        user,
        session_maker,
        100.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )
    second = await _tx(
        account,
        expense_category,
        user,
        session_maker,
        50.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )
    deleted, missing = await TransactionService.bulk_delete(
        ids=[first.id, second.id, 999_999], user_id=user.id, session_maker=session_maker
    )

    refreshed = await AccountService.get_by_user(
        account.id, user.id, session_maker=session_maker
    )
    assert deleted == 2
    assert missing == [999_999]
    assert refreshed.balance == 1000.0


@pytest.mark.asyncio
async def test_bulk_delete_does_not_touch_foreign_records(
    user, other_user, account, expense_category, session_maker
):
    transaction = await _tx(
        account,
        expense_category,
        user,
        session_maker,
        100.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )

    deleted, missing = await TransactionService.bulk_delete(
        ids=[transaction.id], user_id=other_user.id, session_maker=session_maker
    )

    assert deleted == 0
    assert missing == [transaction.id]
    assert (
        await TransactionService.count_by_user(user.id, session_maker=session_maker)
        == 1
    )


# --------------------------------------------------------------------------- #
#  Валюты
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_currency_rates_are_relative_to_base(currencies, session_maker):
    # В фикстуре: USD — 1.0 к базовой, EUR — 1.1
    rates = await CurrencyService.get_rates(base="USD", session_maker=session_maker)
    by_code = {rate.code: rate for rate in rates}

    assert by_code["USD"].rate == 1.0
    assert by_code["USD"].is_base is True
    # 1 USD = 1 / 1.1 EUR
    assert by_code["EUR"].rate == pytest.approx(0.909091, rel=1e-4)

    as_euro = await CurrencyService.get_rates(base="EUR", session_maker=session_maker)
    by_code = {rate.code: rate for rate in as_euro}
    # 1 EUR = 1.1 USD
    assert by_code["USD"].rate == pytest.approx(1.1)
    assert by_code["EUR"].is_base is True


@pytest.mark.asyncio
async def test_currency_rates_reject_unknown_base(currencies, session_maker):
    with pytest.raises(HTTPException) as error:
        await CurrencyService.get_rates(base="XXX", session_maker=session_maker)

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_account_created_with_excluded_flag_defaults_to_false(
    user, currencies, session_maker
):
    created = await AccountService.create_for_user(
        schema=AccountCreate(name="Spare", type=AccountType.SAVINGS, currency_id="USD"),
        user_id=user.id,
        session_maker=session_maker,
    )

    assert created.is_excluded is False
