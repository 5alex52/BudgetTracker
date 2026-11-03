"""Тесты аналитики: итоги, ряды, разбивки, отчёт по месяцам."""

from datetime import datetime
from datetime import timedelta

import pytest
from fastapi import HTTPException
from src.analytics.service import AnalyticsService
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


async def _make_transaction(
    account,
    category,
    user,
    session_maker,
    amount: float,
    transaction_type: TransactionType,
    when: datetime,
    note: str = "",
):
    """Создаёт запись напрямую через сервис (он же пересчитывает баланс счёта)."""
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


@pytest.mark.asyncio
async def test_summary_counts_income_and_expense(user, account, expense_category, income_category, session_maker):
    await _make_transaction(
        account,
        income_category,
        user,
        session_maker,
        1000.0,
        TransactionType.INCOME,
        PERIOD_START,
    )
    await _make_transaction(
        account,
        expense_category,
        user,
        session_maker,
        250.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )

    summary = await AnalyticsService.summary(
        user_id=user.id,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        session_maker=session_maker,
    )

    assert summary.income == 1000.0
    assert summary.expense == 250.0
    assert summary.net == 750.0
    assert summary.transactions_count == 2


@pytest.mark.asyncio
async def test_summary_does_not_count_transfers_as_income_or_expense(user, account, session_maker):
    """Перевод двигает остаток, но не является ни доходом, ни расходом."""
    transfer_category = await CategoryService.create_for_user(
        schema=CategoryCreate(name="Transfer", type=CategoryType.TRANSFER),
        user_id=user.id,
        session_maker=session_maker,
    )
    await _make_transaction(
        account,
        transfer_category,
        user,
        session_maker,
        500.0,
        TransactionType.TRANSFER,
        PERIOD_START,
    )

    summary = await AnalyticsService.summary(
        user_id=user.id,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        compare=False,
        session_maker=session_maker,
    )

    assert summary.income == 0.0
    assert summary.expense == 0.0
    assert summary.transactions_count == 0


@pytest.mark.asyncio
async def test_summary_compares_with_previous_period(user, account, income_category, session_maker):
    # Прошлый период (сентябрь): доход 500
    await _make_transaction(
        account,
        income_category,
        user,
        session_maker,
        500.0,
        TransactionType.INCOME,
        datetime(2025, 9, 15),
    )
    # Текущий период (октябрь): доход 1000 — рост на 100 %
    await _make_transaction(
        account,
        income_category,
        user,
        session_maker,
        1000.0,
        TransactionType.INCOME,
        datetime(2025, 10, 15),
    )
    summary = await AnalyticsService.summary(
        user_id=user.id,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        compare=True,
        session_maker=session_maker,
    )

    assert summary.previous is not None
    assert summary.previous.income == 500.0
    assert summary.change is not None
    assert summary.change.income == 100.0


@pytest.mark.asyncio
async def test_summary_without_compare_has_no_previous(user, account, income_category, session_maker):
    await _make_transaction(
        account,
        income_category,
        user,
        session_maker,
        100.0,
        TransactionType.INCOME,
        PERIOD_START,
    )

    summary = await AnalyticsService.summary(
        user_id=user.id,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        compare=False,
        session_maker=session_maker,
    )

    assert summary.previous is None
    assert summary.change is None


@pytest.mark.asyncio
async def test_summary_converts_currency_to_base(user, session_maker, currencies, premium_entitlements):
    """Итоги складываются в базовой валюте: 100 EUR при курсе 1.1 — это 110 USD."""
    euro_account = await AccountService.create_for_user(
        schema=AccountCreate(name="Euro", type=AccountType.CASH, currency_id="EUR", balance=0.0),
        user_id=user.id,
        session_maker=session_maker,
    )
    category = await CategoryService.create_for_user(
        schema=CategoryCreate(name="Salary", type=CategoryType.INCOME),
        user_id=user.id,
        session_maker=session_maker,
    )
    await _make_transaction(
        euro_account,
        category,
        user,
        session_maker,
        100.0,
        TransactionType.INCOME,
        PERIOD_START,
    )

    summary = await AnalyticsService.summary(
        user_id=user.id,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        compare=False,
        session_maker=session_maker,
    )

    assert summary.income == 110.0


@pytest.mark.asyncio
async def test_summary_uses_personal_currency_rate(user, session_maker, currencies, premium_entitlements):
    """Личный курс пользователя важнее справочного: 100 EUR по 2.0 — это 200 USD."""
    await CurrencyService.set_user_rate(code="EUR", rate=2.0, user_id=user.id, session_maker=session_maker)
    euro_account = await AccountService.create_for_user(
        schema=AccountCreate(name="Euro", type=AccountType.CASH, currency_id="EUR", balance=0.0),
        user_id=user.id,
        session_maker=session_maker,
    )
    category = await CategoryService.create_for_user(
        schema=CategoryCreate(name="Salary", type=CategoryType.INCOME),
        user_id=user.id,
        session_maker=session_maker,
    )
    await _make_transaction(
        euro_account,
        category,
        user,
        session_maker,
        100.0,
        TransactionType.INCOME,
        PERIOD_START,
    )

    summary = await AnalyticsService.summary(
        user_id=user.id,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        compare=False,
        session_maker=session_maker,
    )

    assert summary.income == 200.0


@pytest.mark.asyncio
async def test_excluded_account_is_ignored_by_statistics(
    user, account, second_account, expense_category, session_maker
):
    await _make_transaction(
        account,
        expense_category,
        user,
        session_maker,
        100.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )
    await _make_transaction(
        second_account,
        expense_category,
        user,
        session_maker,
        500.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )

    await AccountService.set_excluded(
        account_id=second_account.id,
        user_id=user.id,
        is_excluded=True,
        session_maker=session_maker,
    )

    summary = await AnalyticsService.summary(
        user_id=user.id,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        compare=False,
        session_maker=session_maker,
    )

    assert summary.expense == 100.0
    assert summary.transactions_count == 1


@pytest.mark.asyncio
async def test_balance_overview_skips_excluded_accounts(user, account, second_account, session_maker):
    await AccountService.set_excluded(
        account_id=second_account.id,
        user_id=user.id,
        is_excluded=True,
        session_maker=session_maker,
    )

    overview = await AccountService.get_balance_overview(user_id=user.id, session_maker=session_maker)

    assert overview.total == 1000.0
    assert [item.account_id for item in overview.accounts] == [account.id]


@pytest.mark.asyncio
async def test_timeseries_cashflow_by_day(user, account, expense_category, income_category, session_maker):
    await _make_transaction(
        account,
        income_category,
        user,
        session_maker,
        300.0,
        TransactionType.INCOME,
        datetime(2025, 10, 2),
    )
    await _make_transaction(
        account,
        expense_category,
        user,
        session_maker,
        100.0,
        TransactionType.EXPENSE,
        datetime(2025, 10, 2),
    )

    series = await AnalyticsService.timeseries(
        user_id=user.id,
        metric="cashflow",
        group_by="day",
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        session_maker=session_maker,
    )

    assert series.metric == "cashflow"
    assert len(series.points) == 1
    point = series.points[0]
    assert point.income == 300.0
    assert point.expense == 100.0
    assert point.net == 200.0


@pytest.mark.asyncio
async def test_timeseries_cashflow_excludes_transfers(user, account, expense_category, income_category, session_maker):
    """Перевод не должен попадать в расходы графика cashflow."""
    transfer_category = await CategoryService.create_for_user(
        schema=CategoryCreate(name="Transfer", type=CategoryType.TRANSFER),
        user_id=user.id,
        session_maker=session_maker,
    )
    await _make_transaction(
        account,
        income_category,
        user,
        session_maker,
        300.0,
        TransactionType.INCOME,
        datetime(2025, 10, 2),
    )
    await _make_transaction(
        account,
        expense_category,
        user,
        session_maker,
        100.0,
        TransactionType.EXPENSE,
        datetime(2025, 10, 2),
    )
    await _make_transaction(
        account,
        transfer_category,
        user,
        session_maker,
        500.0,
        TransactionType.TRANSFER,
        datetime(2025, 10, 2),
    )

    series = await AnalyticsService.timeseries(
        user_id=user.id,
        metric="cashflow",
        group_by="day",
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        session_maker=session_maker,
    )

    point = series.points[0]
    assert point.income == 300.0
    assert point.expense == 100.0
    assert point.net == 200.0


@pytest.mark.asyncio
async def test_timeseries_balance_ends_at_current_balance(
    user, account, expense_category, income_category, session_maker
):
    await _make_transaction(
        account,
        income_category,
        user,
        session_maker,
        200.0,
        TransactionType.INCOME,
        datetime(2025, 10, 5),
    )
    await _make_transaction(
        account,
        expense_category,
        user,
        session_maker,
        50.0,
        TransactionType.EXPENSE,
        datetime(2025, 10, 20),
    )

    series = await AnalyticsService.timeseries(
        user_id=user.id,
        metric="balance",
        group_by="month",
        start_date=datetime(2025, 10, 1),
        end_date=datetime(2025, 10, 31),
        session_maker=session_maker,
    )

    # Баланс счёта после двух операций: 1000 + 200 - 50
    assert series.points[-1].value == 1150.0


@pytest.mark.asyncio
async def test_timeseries_rejects_unknown_grouping(user, session_maker):
    with pytest.raises(HTTPException) as error:
        await AnalyticsService.timeseries(user_id=user.id, group_by="year", session_maker=session_maker)

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_by_category_shares_and_rollup(user, account, expense_category, session_maker):
    child = await CategoryService.create_for_user(
        schema=CategoryCreate(name="Groceries", type=CategoryType.EXPENSE, parent_id=expense_category.id),
        user_id=user.id,
        session_maker=session_maker,
    )
    other = await CategoryService.create_for_user(
        schema=CategoryCreate(name="Transport", type=CategoryType.EXPENSE),
        user_id=user.id,
        session_maker=session_maker,
    )
    await _make_transaction(account, child, user, session_maker, 75.0, TransactionType.EXPENSE, PERIOD_START)
    await _make_transaction(account, other, user, session_maker, 25.0, TransactionType.EXPENSE, PERIOD_START)

    breakdown = await AnalyticsService.by_category(
        user_id=user.id,
        category_type=CategoryType.EXPENSE,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        session_maker=session_maker,
    )

    assert breakdown.total == 100.0
    shares = {item.name: item.share for item in breakdown.items}
    assert shares["Groceries"] == 75.0
    assert shares["Transport"] == 25.0

    rolled = await AnalyticsService.by_category(
        user_id=user.id,
        category_type=CategoryType.EXPENSE,
        rollup=True,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        session_maker=session_maker,
    )
    # Подкатегория сворачивается в родительскую категорию
    assert [item.name for item in rolled.items] == [expense_category.name, "Transport"]


@pytest.mark.asyncio
async def test_by_category_drill_down_into_children(user, account, expense_category, session_maker):
    child = await CategoryService.create_for_user(
        schema=CategoryCreate(name="Cafe", type=CategoryType.EXPENSE, parent_id=expense_category.id),
        user_id=user.id,
        session_maker=session_maker,
    )
    await _make_transaction(
        account,
        expense_category,
        user,
        session_maker,
        40.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )
    await _make_transaction(account, child, user, session_maker, 60.0, TransactionType.EXPENSE, PERIOD_START)

    drill = await AnalyticsService.by_category(
        user_id=user.id,
        category_type=CategoryType.EXPENSE,
        parent_id=expense_category.id,
        include_children=True,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        session_maker=session_maker,
    )

    assert {item.name for item in drill.items} == {expense_category.name, "Cafe"}
    assert drill.total == 100.0


@pytest.mark.asyncio
async def test_by_category_is_isolated_between_users(user, other_user, account, expense_category, session_maker):
    await _make_transaction(
        account,
        expense_category,
        user,
        session_maker,
        40.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )

    breakdown = await AnalyticsService.by_category(
        user_id=other_user.id,
        category_type=CategoryType.EXPENSE,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        session_maker=session_maker,
    )

    assert breakdown.items == []
    assert breakdown.total == 0.0


@pytest.mark.asyncio
async def test_by_account_reports_turnover(user, account, second_account, expense_category, session_maker):
    await _make_transaction(
        account,
        expense_category,
        user,
        session_maker,
        30.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )
    await _make_transaction(
        second_account,
        expense_category,
        user,
        session_maker,
        70.0,
        TransactionType.EXPENSE,
        PERIOD_START,
    )

    breakdown = await AnalyticsService.by_account(
        user_id=user.id,
        start_date=PERIOD_START,
        end_date=PERIOD_END,
        session_maker=session_maker,
    )

    by_name = {item.name: item.expense for item in breakdown.items}
    assert by_name["Cash"] == 30.0
    assert by_name["Savings"] == 70.0
    assert breakdown.total == -100.0  # нетто: расходы со знаком минус складываются в -100


@pytest.mark.asyncio
async def test_matrix_has_months_and_rows(user, account, expense_category, session_maker):
    await _make_transaction(
        account,
        expense_category,
        user,
        session_maker,
        90.0,
        TransactionType.EXPENSE,
        datetime(2025, 10, 10),
    )
    await _make_transaction(
        account,
        expense_category,
        user,
        session_maker,
        60.0,
        TransactionType.EXPENSE,
        datetime(2025, 9, 10),
    )

    matrix = await AnalyticsService.matrix(
        user_id=user.id,
        months=2,
        category_type=CategoryType.EXPENSE,
        end_date=datetime(2025, 10, 31),
        session_maker=session_maker,
    )

    assert matrix.months == ["2025-09", "2025-10"]
    assert len(matrix.rows) == 1
    assert matrix.rows[0].values == [60.0, 90.0]
    # Рост к предыдущему месяцу: (90 - 60) / 60 * 100
    assert matrix.rows[0].trends[1] == 50.0


@pytest.mark.asyncio
async def test_matrix_rejects_bad_month_count(user, session_maker):
    with pytest.raises(HTTPException) as error:
        await AnalyticsService.matrix(user_id=user.id, months=0, session_maker=session_maker)

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_previous_period_is_adjacent_and_same_length():
    start, end = datetime(2025, 10, 1), datetime(2025, 10, 31)
    previous_start, previous_end = AnalyticsService._previous_period(start, end)

    assert previous_end == start - timedelta(microseconds=1)
    assert previous_end - previous_start == end - start
