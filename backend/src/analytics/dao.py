"""Analytics queries: aggregates over finance transaction records.

The ``analytics`` app reads finance data but never writes to it, so there is no
CRUD here — only SELECTs. Models are imported from finance: this is a read-model,
not a second source of truth.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import List
from typing import Optional

from sqlalchemy import case
from sqlalchemy import func
from sqlalchemy import Select
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.finance.dao import CurrencyDAO
from src.finance.dao import UserCurrencyRateDAO
from src.finance.models import AccountModel
from src.finance.models import CategoryModel
from src.finance.models import CurrencyModel
from src.finance.models import TransactionModel
from src.finance.models import UserCurrencyRateModel
from src.finance.schemas import CategoryType
from src.finance.schemas import TransactionType
from src.users.models import UserModel


class AnalyticsDAO:
    """Aggregates for the Overview and Analytics pages.

    Default convention: amounts are converted to the user's base currency
    (``UserModel.base_currency``) using their personal rates; accounts marked as
    "excluded from statistics" are not counted, and records hidden by rule
    (``is_excluded``) are skipped too.
    """

    #: Valid time series groupings (Postgres date_trunc)
    GROUP_BY_OPTIONS = ("day", "week", "month")

    @classmethod
    async def _base_rate(cls, session: AsyncSession, user_id) -> float:
        """How many base-currency units equal one unit of the base currency.

        The catalog stores rates relative to USD, and the user's base currency
        may be any other currency, so we divide by the rate of the base currency
        itself. The user's personal rate overrides the catalog rate.
        """
        user = await session.get(UserModel, user_id)
        base = (getattr(user, "base_currency", None) or "USD").upper()
        currency = await CurrencyDAO.find_one_or_none(session, code=base)
        if currency is None:
            currency = await CurrencyDAO.find_one_or_none(session, code="USD")
        if currency is None:
            return 1.0
        override = await UserCurrencyRateDAO.find_one(session, user_id, base)
        rate = override.rate if override is not None else currency.exchange_rate_to_base
        return float(rate) if rate and rate > 0 else 1.0

    @classmethod
    def _effective_rate(cls, user_id, currency_code_column):
        """Currency rate considering the user's personal rate.

        The catalog stores rates relative to USD, but the user may set their own
        rate. For all aggregates the personal rate is what matters: otherwise the
        Analytics page totals would disagree with currency settings.
        """
        override = (
            select(UserCurrencyRateModel.rate)
            .where(
                UserCurrencyRateModel.user_id == user_id,
                UserCurrencyRateModel.code == currency_code_column,
            )
            .scalar_subquery()
        )
        return func.coalesce(override, CurrencyModel.exchange_rate_to_base)

    @classmethod
    def _statistics_condition(cls) -> tuple:
        """Conditions for "participates in statistics": account not excluded and record not hidden by rule."""
        return (
            AccountModel.is_excluded.is_(False),
            TransactionModel.is_excluded.is_(False),
        )

    @classmethod
    def _scope(
        cls,
        user_id,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category_type: Optional[CategoryType] = None,
        category_ids: Optional[Sequence[int]] = None,
        account_ids: Optional[Sequence[int]] = None,
        only_statistics: bool = True,
        base_rate: float = 1.0,
    ) -> Select:
        """Flat slice of the user's records with the amount already converted to the base currency."""
        divisor = base_rate if base_rate and base_rate > 0 else 1.0
        rate = cls._effective_rate(user_id, CurrencyModel.code)
        amount_base = TransactionModel.amount * rate / divisor
        signed = case(
            (TransactionModel.type == TransactionType.INCOME, TransactionModel.amount),
            else_=-TransactionModel.amount,
        )
        stmt = (
            select(
                TransactionModel.id.label("id"),
                TransactionModel.date.label("date"),
                TransactionModel.type.label("type"),
                TransactionModel.amount.label("amount"),
                TransactionModel.category_id.label("category_id"),
                TransactionModel.account_id.label("account_id"),
                TransactionModel.currency_id.label("currency_id"),
                AccountModel.name.label("account_name"),
                AccountModel.currency_id.label("account_currency_id"),
                CategoryModel.name.label("category_name"),
                CategoryModel.color.label("category_color"),
                CategoryModel.icon.label("category_icon"),
                CategoryModel.parent_id.label("category_parent_id"),
                CategoryModel.type.label("category_type"),
                amount_base.label("amount_base"),
                (signed * rate / divisor).label("signed_base"),
            )
            .select_from(TransactionModel)
            .join(AccountModel, TransactionModel.account_id == AccountModel.id)
            .join(CategoryModel, TransactionModel.category_id == CategoryModel.id)
            .join(CurrencyModel, TransactionModel.currency_id == CurrencyModel.code)
            .where(
                AccountModel.user_id == user_id,
                # Transfers are neither income nor expense: they must not appear in
                # expense breakdowns, KPI, or the analytics record counter.
                TransactionModel.type != TransactionType.TRANSFER,
            )
        )
        if only_statistics:
            stmt = stmt.where(*cls._statistics_condition())
        if start_date is not None:
            stmt = stmt.where(TransactionModel.date >= start_date)
        if end_date is not None:
            stmt = stmt.where(TransactionModel.date <= end_date)
        if category_type is not None:
            stmt = stmt.where(TransactionModel.type == TransactionType(category_type.value))
        if category_ids:
            stmt = stmt.where(TransactionModel.category_id.in_(list(category_ids)))
        if account_ids:
            stmt = stmt.where(TransactionModel.account_id.in_(list(account_ids)))
        return stmt

    @classmethod
    async def total_balance_base(cls, session: AsyncSession, user_id) -> float:
        """Sum of account balances in the base currency — the starting point for the balance chart."""
        base_rate = await cls._base_rate(session, user_id)
        divisor = base_rate if base_rate and base_rate > 0 else 1.0
        rate = cls._effective_rate(user_id, CurrencyModel.code)
        stmt = (
            select(
                func.coalesce(
                    func.sum(AccountModel.balance * rate / divisor),
                    0.0,
                )
            )
            .select_from(AccountModel)
            .join(CurrencyModel, AccountModel.currency_id == CurrencyModel.code)
            .where(
                AccountModel.user_id == user_id,
                # Archived accounts participate in statistics — the user can
                # view totals for any period. Accounts excluded from statistics
                # do not affect either balance or turnover.
                AccountModel.is_excluded.is_(False),
            )
        )
        result = await session.execute(stmt)
        return round(float(result.scalar() or 0.0), 2)

    @classmethod
    async def totals_by_type(
        cls,
        session: AsyncSession,
        user_id,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        only_statistics: bool = True,
        account_ids: Optional[Sequence[int]] = None,
    ) -> dict:
        """Income, expense, and record count for the period (in the base currency)."""
        base_rate = await cls._base_rate(session, user_id)
        scope = cls._scope(
            user_id,
            start_date,
            end_date,
            only_statistics=only_statistics,
            account_ids=account_ids,
            base_rate=base_rate,
        ).subquery()
        stmt = select(
            scope.c.type,
            func.coalesce(func.sum(scope.c.amount_base), 0.0).label("total"),
            func.count(scope.c.id).label("count"),
        ).group_by(scope.c.type)
        result = await session.execute(stmt)
        return {
            row.type.value if hasattr(row.type, "value") else str(row.type): (
                float(row.total),
                int(row.count),
            )
            for row in result.all()
        }

    @classmethod
    async def series_by_bucket(
        cls,
        session: AsyncSession,
        user_id,
        group_by: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        only_statistics: bool = True,
    ) -> List:
        """Income and expense by day/week/month."""
        base_rate = await cls._base_rate(session, user_id)
        divisor = base_rate if base_rate and base_rate > 0 else 1.0
        rate = cls._effective_rate(user_id, CurrencyModel.code)
        when = func.date_trunc(group_by, TransactionModel.date).label("bucket")
        stmt = (
            select(
                when,
                TransactionModel.type.label("type"),
                func.coalesce(
                    func.sum(TransactionModel.amount * rate / divisor),
                    0.0,
                ).label("total"),
            )
            # select_from is required: the column list doesn't reference transactions directly,
            # and without it FROM is inferred from expressions — joins would start from the wrong table
            .select_from(TransactionModel)
            .join(AccountModel, TransactionModel.account_id == AccountModel.id)
            .join(CurrencyModel, TransactionModel.currency_id == CurrencyModel.code)
            .where(
                AccountModel.user_id == user_id,
                TransactionModel.type != TransactionType.TRANSFER,
            )
        )
        if only_statistics:
            stmt = stmt.where(*cls._statistics_condition())
        if start_date is not None:
            stmt = stmt.where(TransactionModel.date >= start_date)
        if end_date is not None:
            stmt = stmt.where(TransactionModel.date <= end_date)
        stmt = stmt.group_by(when, TransactionModel.type).order_by(when)
        result = await session.execute(stmt)
        return list(result.all())

    @classmethod
    async def balances_by_bucket(
        cls,
        session: AsyncSession,
        user_id,
        group_by: str,
        start_date: datetime,
        end_date: datetime,
        only_statistics: bool = True,
    ) -> List:
        """Signed turnover by bucket — used to build the balance curve."""
        base_rate = await cls._base_rate(session, user_id)
        divisor = base_rate if base_rate and base_rate > 0 else 1.0
        rate = cls._effective_rate(user_id, CurrencyModel.code)
        when = func.date_trunc(group_by, TransactionModel.date).label("bucket")
        signed = case(
            (TransactionModel.type == TransactionType.INCOME, TransactionModel.amount),
            else_=-TransactionModel.amount,
        )
        stmt = (
            select(
                when,
                func.coalesce(
                    func.sum(signed * rate / divisor),
                    0.0,
                ).label("total"),
            )
            .select_from(TransactionModel)
            .join(AccountModel, TransactionModel.account_id == AccountModel.id)
            .join(CurrencyModel, TransactionModel.currency_id == CurrencyModel.code)
            .where(
                AccountModel.user_id == user_id,
                TransactionModel.type != TransactionType.TRANSFER,
                TransactionModel.date >= start_date,
                TransactionModel.date <= end_date,
            )
        )
        if only_statistics:
            stmt = stmt.where(*cls._statistics_condition())
        stmt = stmt.group_by(when).order_by(when)
        result = await session.execute(stmt)
        return list(result.all())

    @classmethod
    async def signed_total_after(
        cls,
        session: AsyncSession,
        user_id,
        moment: datetime,
        only_statistics: bool = True,
    ) -> float:
        """Total signed turnover after the given moment."""
        base_rate = await cls._base_rate(session, user_id)
        divisor = base_rate if base_rate and base_rate > 0 else 1.0
        rate = cls._effective_rate(user_id, CurrencyModel.code)
        signed = case(
            (TransactionModel.type == TransactionType.INCOME, TransactionModel.amount),
            else_=-TransactionModel.amount,
        )
        stmt = (
            select(
                func.coalesce(
                    func.sum(signed * rate / divisor),
                    0.0,
                )
            )
            .select_from(TransactionModel)
            .join(AccountModel, TransactionModel.account_id == AccountModel.id)
            .join(CurrencyModel, TransactionModel.currency_id == CurrencyModel.code)
            .where(
                AccountModel.user_id == user_id,
                TransactionModel.type != TransactionType.TRANSFER,
                TransactionModel.date > moment,
            )
        )
        if only_statistics:
            stmt = stmt.where(*cls._statistics_condition())
        result = await session.execute(stmt)
        return float(result.scalar() or 0.0)

    @classmethod
    async def totals_by_category(
        cls,
        session: AsyncSession,
        user_id,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category_type: Optional[CategoryType] = None,
        rollup: bool = False,
        only_statistics: bool = True,
    ) -> List:
        """Totals by category; ``rollup`` folds subcategories into the parent."""
        base_rate = await cls._base_rate(session, user_id)
        scope = cls._scope(
            user_id,
            start_date,
            end_date,
            category_type=category_type,
            only_statistics=only_statistics,
            base_rate=base_rate,
        ).subquery()
        total = func.coalesce(func.sum(scope.c.amount_base), 0.0).label("total")
        count = func.count(scope.c.id).label("count")

        if rollup:
            group_id = func.coalesce(scope.c.category_parent_id, scope.c.category_id).label("group_id")
            stmt = select(group_id, total, count).group_by(group_id).order_by(total.desc())
        else:
            stmt = (
                select(
                    scope.c.category_id.label("group_id"),
                    scope.c.category_name.label("name"),
                    scope.c.category_color.label("color"),
                    scope.c.category_icon.label("icon"),
                    scope.c.category_parent_id.label("parent_id"),
                    scope.c.category_type.label("category_type"),
                    total,
                    count,
                )
                .group_by(
                    scope.c.category_id,
                    scope.c.category_name,
                    scope.c.category_color,
                    scope.c.category_icon,
                    scope.c.category_parent_id,
                    scope.c.category_type,
                )
                .order_by(total.desc())
            )

        result = await session.execute(stmt)
        return list(result.all())

    @classmethod
    async def totals_by_account(
        cls,
        session: AsyncSession,
        user_id,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        only_statistics: bool = True,
    ) -> List:
        """Account turnover for the period."""
        base_rate = await cls._base_rate(session, user_id)
        scope = cls._scope(
            user_id,
            start_date,
            end_date,
            only_statistics=only_statistics,
            base_rate=base_rate,
        ).subquery()
        income = func.coalesce(
            func.sum(
                case(
                    (scope.c.type == TransactionType.INCOME, scope.c.amount_base),
                    else_=0.0,
                )
            ),
            0.0,
        )
        expense = func.coalesce(
            func.sum(
                case(
                    (scope.c.type == TransactionType.EXPENSE, scope.c.amount_base),
                    else_=0.0,
                )
            ),
            0.0,
        )
        stmt = (
            select(
                scope.c.account_id.label("account_id"),
                scope.c.account_name.label("name"),
                scope.c.account_currency_id.label("currency_id"),
                income.label("income"),
                expense.label("expense"),
                func.count(scope.c.id).label("count"),
            )
            .group_by(scope.c.account_id, scope.c.account_name, scope.c.account_currency_id)
            .order_by(func.sum(scope.c.amount_base).desc())
        )
        result = await session.execute(stmt)
        return list(result.all())

    @classmethod
    async def totals_by_category_and_month(
        cls,
        session: AsyncSession,
        user_id,
        group_by: str,
        start_date: datetime,
        end_date: datetime,
        category_type: Optional[CategoryType] = None,
        rollup: bool = False,
        only_statistics: bool = True,
        account_ids: Optional[Sequence[int]] = None,
    ) -> List:
        """Categories × months report: totals for (category, bucket) pairs."""
        base_rate = await cls._base_rate(session, user_id)
        scope = cls._scope(
            user_id,
            start_date,
            end_date,
            category_type=category_type,
            only_statistics=only_statistics,
            account_ids=account_ids,
            base_rate=base_rate,
        ).subquery()
        bucket = func.date_trunc(group_by, scope.c.date).label("bucket")
        group_id = (
            func.coalesce(scope.c.category_parent_id, scope.c.category_id) if rollup else scope.c.category_id
        ).label("group_id")
        stmt = (
            select(
                group_id,
                bucket,
                func.coalesce(func.sum(scope.c.amount_base), 0.0).label("total"),
            )
            .group_by(group_id, bucket)
            .order_by(bucket)
        )
        result = await session.execute(stmt)
        return list(result.all())
