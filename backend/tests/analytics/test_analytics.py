"""Analytics tests: summaries, series, breakdowns, monthly report."""

from datetime import datetime
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from src.analytics.dao import AnalyticsDAO
from src.analytics.service import AnalyticsService
from src.crypto.models import CryptoBalanceSnapshotModel
from src.crypto.models import CryptoPriceDailyModel
from src.crypto.schemas import HoldingIn
from src.crypto.schemas import SnapshotSource
from src.crypto.schemas import WalletCreate
from src.crypto.schemas import WalletKind
from src.crypto.service import CryptoService
from src.finance.models import AccountModel
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
    transfer_account_id=None,
):
    """Creates a record directly via the service (which also recalculates the account balance)."""
    return await TransactionService.create_for_user(
        schema=TransactionCreate(
            account_id=account.id,
            category_id=category.id,
            transfer_account_id=transfer_account_id,
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
async def test_summary_does_not_count_transfers_as_income_or_expense(user, account, second_account, session_maker):
    """Transfers move the balance but are neither income nor expense."""
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
        transfer_account_id=second_account.id,
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
    # Previous period (September): income 500
    await _make_transaction(
        account,
        income_category,
        user,
        session_maker,
        500.0,
        TransactionType.INCOME,
        datetime(2025, 9, 15),
    )
    # Current period (October): income 1000 — 100% growth
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
async def test_summary_converts_currency_to_base(user, session_maker, currencies):
    """Totals are aggregated in the base currency: 100 EUR at rate 1.1 is 110 USD."""
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
async def test_summary_uses_personal_currency_rate(user, session_maker, currencies):
    """The user's personal rate takes precedence over the catalog: 100 EUR at 1 EUR = 2 USD is 200 USD."""
    await CurrencyService.set_user_rate(code="EUR", rate=0.5, user_id=user.id, session_maker=session_maker)
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
async def test_timeseries_cashflow_excludes_transfers(
    user, account, second_account, expense_category, income_category, session_maker
):
    """A transfer must not appear in the cashflow chart expenses."""
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
        transfer_account_id=second_account.id,
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

    # Account balance after two operations: 1000 + 200 - 50
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
    # Subcategory rolls up into the parent category
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
    assert breakdown.total == -100.0  # net: negative expenses sum to -100


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
    # Growth vs previous month: (90 - 60) / 60 * 100
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


# --- wallet accounts feed the main balance ------------------------------------


@pytest.mark.asyncio
async def test_total_balance_includes_wallet_accounts(user, account, currencies, session_maker):
    """A wallet account counts like any other account; excluded ones do not."""
    today = datetime.now().date()
    async with session_maker() as session:
        session.add_all(
            [
                CryptoPriceDailyModel(asset_code="BTC", day=today, price_usd=Decimal("60000")),
                CryptoPriceDailyModel(asset_code="ETH", day=today, price_usd=Decimal("3000")),
            ]
        )
        await session.commit()
    await CryptoService.create_for_user(
        WalletCreate(name="Wallet", kind=WalletKind.MANUAL, holdings=[HoldingIn(asset_code="BTC", amount=1)]),
        user.id,
        session_maker,
    )
    hidden = await CryptoService.create_for_user(
        WalletCreate(name="Hidden", kind=WalletKind.MANUAL, holdings=[HoldingIn(asset_code="ETH", amount=2)]),
        user.id,
        session_maker,
    )
    # Excluding the wallet account takes its synced balance out of the totals.
    async with session_maker() as session:
        row = await session.get(AccountModel, hidden.id)
        row.is_excluded = True
        await session.commit()

    async with session_maker() as session:
        # account 1000 USD + wallet account 1 BTC × 60000; hidden (ETH 2 × 3000) excluded
        assert await AnalyticsDAO.total_balance_base(session, user.id) == pytest.approx(61000.0)


@pytest.mark.asyncio
async def test_balance_series_includes_wallet_value(user, account, currencies, session_maker):
    """Daily snapshots price the curve: days before the first snapshot carry the
    opening balance (earliest known amount × earliest known price), that day's
    amount × that day's price after."""
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    async with session_maker() as session:
        session.add_all(
            [
                CryptoPriceDailyModel(asset_code="BTC", day=yesterday, price_usd=Decimal("50000")),
                CryptoPriceDailyModel(asset_code="BTC", day=today, price_usd=Decimal("60000")),
            ]
        )
        await session.commit()
    wallet = await CryptoService.create_for_user(
        WalletCreate(name="Wallet", kind=WalletKind.MANUAL, holdings=[HoldingIn(asset_code="BTC", amount=1)]),
        user.id,
        session_maker,
    )
    async with session_maker() as session:
        session.add(
            CryptoBalanceSnapshotModel(
                account_id=wallet.id,
                asset_code="BTC",
                day=yesterday,
                amount=Decimal("1"),
                price_usd=Decimal("50000"),
                source=SnapshotSource.BACKFILL,
                taken_at=datetime.now(),
            )
        )
        await session.commit()

    series = await AnalyticsService.timeseries(
        user_id=user.id,
        metric="balance",
        group_by="day",
        start_date=datetime.combine(today - timedelta(days=2), datetime.min.time()),
        end_date=datetime.now(),
        session_maker=session_maker,
    )
    values = {point.date.date(): point.value for point in series.points}
    assert values[today - timedelta(days=2)] == pytest.approx(
        51000.0
    )  # before the first snapshot: opening 1 BTC × earliest price
    assert values[yesterday] == pytest.approx(51000.0)  # 1 BTC carried, priced at 50000
    assert values[today] == pytest.approx(61000.0)  # today's snapshot × today's price = current total


def test_bucket_bounds_snap_to_date_trunc_grid():
    """Bounds must match the DAO's date_trunc buckets even for unaligned period edges."""
    start = datetime(2025, 10, 8, 15, 30)  # a Wednesday
    end = datetime(2025, 10, 12, 9, 0)

    day = AnalyticsService._bucket_bounds("day", start, end)
    assert day[0] == datetime(2025, 10, 8)
    assert all(b.hour == 0 and b.minute == 0 and b.second == 0 for b in day)

    week = AnalyticsService._bucket_bounds("week", start, end)
    assert week[0] == datetime(2025, 10, 6)  # Monday of that week

    month = AnalyticsService._bucket_bounds("month", start, datetime(2025, 12, 20, 9, 0))
    assert month == [datetime(2025, 10, 1), datetime(2025, 11, 1), datetime(2025, 12, 1)]
