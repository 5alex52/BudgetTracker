"""Сервис аналитики: собирает агрегаты из DAO в ответы API."""

import logging

logger = logging.getLogger(__name__)

from datetime import datetime
from datetime import timedelta
from typing import List
from typing import Optional

from fastapi import HTTPException
from fastapi import status
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.database import async_session_maker
from src.finance.dao import CategoryDAO
from src.finance.schemas import CategoryType
from src.finance.schemas import TransactionType
from src.finance.utils import normalize_period

from .dao import AnalyticsDAO
from .schemas import AccountShare
from .schemas import AccountShareResponse
from .schemas import AnalyticsSummary
from .schemas import BalancePoint
from .schemas import CategoryShare
from .schemas import CategoryShareResponse
from .schemas import MatrixResponse
from .schemas import MatrixRow
from .schemas import PeriodChange
from .schemas import PeriodTotals
from .schemas import SeriesPoint
from .schemas import TimeseriesResponse

from ..cache import Cache


def _resolve_session_maker(
    session_maker: Optional[async_sessionmaker],
) -> async_sessionmaker:
    return session_maker or async_session_maker


class AnalyticsService:
    """Агрегаты для «Обзора» и «Аналитики».

    Класс не привязан к одной таблице, поэтому наследуется напрямую от ``object``:
    viewset вызывает сервис, сервис ходит в DAO — та же связка слоёв, что и в
    остальных приложениях, только без CRUD.
    """

    @staticmethod
    def _percent(now: float, before: float) -> Optional[float]:
        """Изменение в процентах; ``None``, если сравнивать не с чем."""
        if before == 0:
            return None
        return round((now - before) / abs(before) * 100, 2)

    @classmethod
    def _previous_period(cls, start_date: datetime, end_date: datetime) -> tuple:
        """Предыдущий период той же длины, вплотную к текущему."""
        length = end_date - start_date
        previous_end = start_date - timedelta(microseconds=1)
        previous_start = previous_end - length
        return previous_start, previous_end

    @classmethod
    def _totals(cls, rows: dict) -> tuple:
        income = round(rows.get("income", (0.0, 0))[0], 2)
        expense = round(rows.get("expense", (0.0, 0))[0], 2)
        count = sum(value[1] for value in rows.values())
        return income, expense, count

    @classmethod
    async def summary(
        cls,
        user_id,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        compare: bool = True,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> AnalyticsSummary:
        """Итоги периода с минутным кешем.

        «Обзор» перерисовывается часто, а цифры меняются только после записи,
        поэтому ответ живёт в Redis и сбрасывается при любой операции с записями.
        """
        start_date, end_date = normalize_period(start_date, end_date)
        key = Cache.make_key(
            "analytics:summary",
            user=str(user_id),
            start=start_date,
            end=end_date,
            compare=compare,
        )
        hit = await Cache.get(key)
        if hit is not None:
            return AnalyticsSummary(**hit)

        result = await cls._summary(user_id, start_date, end_date, compare, session_maker)
        await Cache.set(key, result.model_dump(), ttl=60)
        return result

    @classmethod
    async def _summary(
        cls,
        user_id,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        compare: bool,
        session_maker: Optional[async_sessionmaker],
    ) -> AnalyticsSummary:
        """Расчёт итогов без кеша."""
        start_date, end_date = normalize_period(start_date, end_date)
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            rows = await AnalyticsDAO.totals_by_type(session, user_id, start_date=start_date, end_date=end_date)
            income, expense, count = cls._totals(rows)

            previous = None
            change = None
            # Сравнивать можно только когда период задан явно: иначе непонятно, с чем
            if compare and start_date is not None and end_date is not None:
                previous_start, previous_end = cls._previous_period(start_date, end_date)
                previous_rows = await AnalyticsDAO.totals_by_type(
                    session, user_id, start_date=previous_start, end_date=previous_end
                )
                previous_income, previous_expense, previous_count = cls._totals(previous_rows)
                previous = PeriodTotals(
                    start_date=previous_start,
                    end_date=previous_end,
                    income=previous_income,
                    expense=previous_expense,
                    net=round(previous_income - previous_expense, 2),
                    transactions_count=previous_count,
                )
                change = PeriodChange(
                    income=cls._percent(income, previous_income),
                    expense=cls._percent(expense, previous_expense),
                    net=cls._percent(income - expense, previous_income - previous_expense),
                )

        return AnalyticsSummary(
            start_date=start_date,
            end_date=end_date,
            income=income,
            expense=expense,
            net=round(income - expense, 2),
            transactions_count=count,
            previous=previous,
            change=change,
        )

    @classmethod
    def _bucket_bounds(cls, group_by: str, start_date: datetime, end_date: datetime) -> List[datetime]:
        """Границы интервалов между началом и концом периода."""
        step = {"day": timedelta(days=1), "week": timedelta(weeks=1), "month": None}[group_by]
        bounds: List[datetime] = []
        cursor = start_date
        while cursor <= end_date:
            bounds.append(cursor)
            if step is not None:
                cursor = cursor + step
            else:
                cursor = (cursor.replace(day=1) + timedelta(days=32)).replace(day=1)
        return bounds

    @classmethod
    async def timeseries(
        cls,
        user_id,
        metric: str = "cashflow",
        group_by: str = "day",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> TimeseriesResponse:
        """Точки графика с минутным кешем: графики не должны ходить в БД каждый раз."""
        start_date, end_date = normalize_period(start_date, end_date)
        key = Cache.make_key(
            "analytics:timeseries",
            user=str(user_id),
            metric=metric,
            group=group_by,
            start=start_date,
            end=end_date,
        )
        hit = await Cache.get(key)
        if hit is not None:
            return TimeseriesResponse(**hit)

        result = await cls._timeseries(user_id, metric, group_by, start_date, end_date, session_maker)
        await Cache.set(key, result.model_dump(), ttl=60)
        return result

    @classmethod
    async def _timeseries(
        cls,
        user_id,
        metric: str,
        group_by: str,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        session_maker: Optional[async_sessionmaker],
    ) -> TimeseriesResponse:
        """Расчёт точек графика без кеша."""
        if group_by not in AnalyticsDAO.GROUP_BY_OPTIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"group_by must be one of: {', '.join(AnalyticsDAO.GROUP_BY_OPTIONS)}",
            )
        if metric not in {"cashflow", "balance"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="metric must be one of: cashflow, balance",
            )
        start_date, end_date = normalize_period(start_date, end_date)
        if start_date is None or end_date is None:
            # Период по умолчанию — последние 30 дней: график без границ не построить
            end_date = end_date or datetime.now()
            start_date = start_date or (end_date - timedelta(days=30))

        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            if metric == "balance":
                return await cls._balance_series(session, user_id, group_by, start_date, end_date)

            rows = await AnalyticsDAO.series_by_bucket(
                session, user_id, group_by, start_date=start_date, end_date=end_date
            )
            points: dict = {}
            for row in rows:
                point = points.setdefault(row.bucket, SeriesPoint(date=row.bucket))
                if row.type == TransactionType.INCOME:
                    point.income = round(float(row.total), 2)
                else:
                    # Расход отдаём положительным числом: знак — дело отрисовки графика,
                    # а в API все суммы сравнимы между собой (как в summary)
                    point.expense = round(float(row.total), 2)
            for point in points.values():
                point.net = round(point.income - point.expense, 2)

            ordered = [points[key] for key in sorted(points)]
            return TimeseriesResponse(group_by=group_by, metric=metric, points=ordered)

    @classmethod
    async def _balance_series(cls, session, user_id, group_by, start_date, end_date) -> TimeseriesResponse:
        """Остаток на конец интервала: текущий баланс минус всё, что случилось позже."""
        current_total = await AnalyticsDAO.total_balance_base(session, user_id)
        rows = await AnalyticsDAO.balances_by_bucket(session, user_id, group_by, start_date, end_date)
        after = await AnalyticsDAO.signed_total_after(session, user_id, end_date)

        deltas = {row.bucket: float(row.total) for row in rows}
        bounds = cls._bucket_bounds(group_by, start_date, end_date)
        points: List[BalancePoint] = []
        tail = after
        for bound in reversed(bounds):
            value = current_total - tail
            points.append(BalancePoint(date=bound, value=round(value, 2)))
            tail += deltas.get(bound, 0.0)
        points.reverse()
        return TimeseriesResponse(group_by=group_by, metric="balance", points=points)

    @classmethod
    async def by_category(
        cls,
        user_id,
        category_type: Optional[CategoryType] = None,
        parent_id: Optional[int] = None,
        include_children: bool = True,
        rollup: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> CategoryShareResponse:
        """Доли категорий за период с минутным кешем."""
        start_date, end_date = normalize_period(start_date, end_date)
        key = Cache.make_key(
            "analytics:by-category",
            user=str(user_id),
            type=category_type.value if category_type is not None else None,
            parent=parent_id,
            children=include_children,
            rollup=rollup,
            start=start_date,
            end=end_date,
        )
        hit = await Cache.get(key)
        if hit is not None:
            return CategoryShareResponse(**hit)

        result = await cls._by_category(
            user_id,
            category_type,
            parent_id,
            include_children,
            rollup,
            start_date,
            end_date,
            session_maker,
        )
        await Cache.set(key, result.model_dump(), ttl=60)
        return result

    @classmethod
    async def _by_category(
        cls,
        user_id,
        category_type: Optional[CategoryType],
        parent_id: Optional[int],
        include_children: bool,
        rollup: bool,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        session_maker: Optional[async_sessionmaker],
    ) -> CategoryShareResponse:
        """Расчёт долей категорий без кеша."""
        start_date, end_date = normalize_period(start_date, end_date)
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            categories = await CategoryDAO.find_all_by_user(session, user_id, limit=500)
            by_id = {category.id: category for category in categories}

            allowed_ids: Optional[List[int]] = None
            if parent_id is not None:
                if parent_id not in by_id:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Category not found",
                    )
                allowed_ids = [parent_id]
                if include_children:
                    allowed_ids += [item.id for item in categories if item.parent_id == parent_id]

            rows = await AnalyticsDAO.totals_by_category(
                session,
                user_id,
                start_date=start_date,
                end_date=end_date,
                category_type=category_type,
                rollup=rollup,
            )

        items: List[CategoryShare] = []
        for row in rows:
            if allowed_ids is not None and row.group_id not in allowed_ids:
                continue
            category = by_id.get(row.group_id)
            if category is None:
                continue
            items.append(
                CategoryShare(
                    category_id=category.id,
                    name=category.name,
                    type=category.type,
                    parent_id=category.parent_id,
                    color=category.color,
                    icon=category.icon,
                    total=round(float(row.total), 2),
                    share=0.0,
                    transactions_count=int(row.count),
                )
            )

        total = round(sum(item.total for item in items), 2)
        for item in items:
            item.share = round(item.total / total * 100, 2) if total else 0.0
        return CategoryShareResponse(items=items, total=total)

    @classmethod
    async def by_account(
        cls,
        user_id,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> AccountShareResponse:
        """Обороты по счетам за период."""
        start_date, end_date = normalize_period(start_date, end_date)
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            rows = await AnalyticsDAO.totals_by_account(session, user_id, start_date=start_date, end_date=end_date)
        items = [
            AccountShare(
                account_id=row.account_id,
                name=row.name,
                currency_id=row.currency_id,
                income=round(float(row.income), 2),
                expense=round(float(row.expense), 2),
                net=round(float(row.income) - float(row.expense), 2),
                transactions_count=int(row.count),
            )
            for row in rows
        ]
        return AccountShareResponse(items=items, total=round(sum(item.net for item in items), 2))

    @classmethod
    async def matrix(
        cls,
        user_id,
        months: int = 6,
        category_type: Optional[CategoryType] = None,
        rollup: bool = True,
        end_date: Optional[datetime] = None,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> MatrixResponse:
        """Отчёт «категории × месяцы» для страницы «Аналитика»."""
        if months < 1 or months > 36:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="months must be between 1 and 36",
            )
        end_date = end_date or datetime.now()
        first_month = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for _ in range(months - 1):
            first_month = (first_month - timedelta(days=1)).replace(day=1)
        start_date = first_month

        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            categories = await CategoryDAO.find_all_by_user(session, user_id, limit=500)
            rows = await AnalyticsDAO.totals_by_category_and_month(
                session,
                user_id,
                "month",
                start_date=start_date,
                end_date=end_date,
                category_type=category_type,
                rollup=rollup,
            )
        by_id = {category.id: category for category in categories}

        month_keys = [
            f"{first_month.year + (first_month.month - 1 + offset) // 12:04d}-"
            f"{(first_month.month - 1 + offset) % 12 + 1:02d}"
            for offset in range(months)
        ]
        values: dict = {}
        for row in rows:
            bucket = row.bucket.strftime("%Y-%m")
            values.setdefault(row.group_id, {}).setdefault(bucket, 0.0)
            values[row.group_id][bucket] += float(row.total)

        matrix_rows: List[MatrixRow] = []
        for group_id, per_month in values.items():
            category = by_id.get(group_id)
            if category is None:
                continue
            series = [round(per_month.get(key, 0.0), 2) for key in month_keys]
            trends: List[Optional[float]] = []
            for index, value in enumerate(series):
                if index == 0:
                    trends.append(None)
                    continue
                trends.append(cls._percent(value, series[index - 1]))
            matrix_rows.append(
                MatrixRow(
                    category_id=category.id,
                    name=category.name,
                    parent_id=category.parent_id,
                    color=category.color,
                    icon=category.icon,
                    values=series,
                    trends=trends,
                )
            )
        matrix_rows.sort(key=lambda row: sum(row.values), reverse=True)
        return MatrixResponse(months=month_keys, rows=matrix_rows)
