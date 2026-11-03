"""ViewSet аналитики: только чтение, поэтому без CRUD-методов базового класса."""

from datetime import datetime
from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.database import get_async_session_maker
from src.finance.schemas import CategoryType
from src.users.schemas import User
from src.viewset import check_permissions

from .permissions import AnalyticsPermission
from .schemas import AccountShareResponse
from .schemas import AnalyticsSummary
from .schemas import CategoryShareResponse
from .schemas import MatrixResponse
from .schemas import TimeseriesResponse
from .service import AnalyticsService


class AnalyticsViewSet:
    """Сводные показатели: не CRUD над одной таблицей, а выборки поверх записей."""

    permission = AnalyticsPermission
    service = AnalyticsService

    @classmethod
    @check_permissions(action="analytics_summary")
    async def summary(
        cls,
        user: User,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        compare: bool = True,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> AnalyticsSummary:
        return await cls.service.summary(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            compare=compare,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="analytics_timeseries")
    async def timeseries(
        cls,
        user: User,
        metric: str = "cashflow",
        group_by: str = "day",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> TimeseriesResponse:
        return await cls.service.timeseries(
            user_id=user.id,
            metric=metric,
            group_by=group_by,
            start_date=start_date,
            end_date=end_date,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="analytics_by_category")
    async def by_category(
        cls,
        user: User,
        category_type: Optional[CategoryType] = None,
        parent_id: Optional[int] = None,
        include_children: bool = True,
        rollup: bool = False,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> CategoryShareResponse:
        return await cls.service.by_category(
            user_id=user.id,
            category_type=category_type,
            parent_id=parent_id,
            include_children=include_children,
            rollup=rollup,
            start_date=start_date,
            end_date=end_date,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="analytics_by_account")
    async def by_account(
        cls,
        user: User,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> AccountShareResponse:
        return await cls.service.by_account(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="analytics_matrix")
    async def matrix(
        cls,
        user: User,
        months: int = 6,
        category_type: Optional[CategoryType] = None,
        rollup: bool = True,
        end_date: Optional[datetime] = None,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> MatrixResponse:
        return await cls.service.matrix(
            user_id=user.id,
            months=months,
            category_type=category_type,
            rollup=rollup,
            end_date=end_date,
            session_maker=session_maker,
        )
