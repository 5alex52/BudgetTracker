"""HTTP-слой аналитики: только GET-эндпоинты."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import Request
from fastapi import status
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.database import get_async_session_maker
from src.finance.schemas import CategoryType
from src.finance.schemas import TransactionType

from .dependencies import CurrentUser
from .schemas import AccountShareResponse
from .schemas import AnalyticsSummary
from .schemas import CategoryShareResponse
from .schemas import MatrixResponse
from .schemas import TimeseriesResponse
from .viewsets import AnalyticsViewSet

analytics_router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@analytics_router.get("/summary", status_code=status.HTTP_200_OK, response_model=AnalyticsSummary)
async def get_analytics_summary(
    request: Request,
    user: CurrentUser,
    start_date: Optional[datetime] = Query(None, description="Начало периода"),
    end_date: Optional[datetime] = Query(None, description="Конец периода"),
    compare: bool = Query(True, description="Сравнить с предыдущим периодом той же длины"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AnalyticsSummary:
    """Доходы, расходы и нетто за период в базовой валюте."""
    return await AnalyticsViewSet.summary(
        request=request,
        user=user,
        start_date=start_date,
        end_date=end_date,
        compare=compare,
        session_maker=session_maker,
    )


@analytics_router.get("/timeseries", status_code=status.HTTP_200_OK, response_model=TimeseriesResponse)
async def get_analytics_timeseries(
    request: Request,
    user: CurrentUser,
    metric: str = Query("cashflow", pattern="^(cashflow|balance)$", description="cashflow или balance"),
    group_by: str = Query("day", pattern="^(day|week|month)$", description="Шаг группировки"),
    start_date: Optional[datetime] = Query(None, description="Начало периода"),
    end_date: Optional[datetime] = Query(None, description="Конец периода"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> TimeseriesResponse:
    """Ряды для графиков «Обзора»: денежный поток или остаток по интервалам."""
    return await AnalyticsViewSet.timeseries(
        request=request,
        user=user,
        metric=metric,
        group_by=group_by,
        start_date=start_date,
        end_date=end_date,
        session_maker=session_maker,
    )


@analytics_router.get("/by-category", status_code=status.HTTP_200_OK, response_model=CategoryShareResponse)
async def get_analytics_by_category(
    request: Request,
    user: CurrentUser,
    transaction_type: Optional[TransactionType] = Query(None, description="Тип записей"),
    parent_id: Optional[int] = Query(None, description="Провалиться в подкатегории этой категории"),
    include_children: bool = Query(True, description="Учитывать подкатегории"),
    rollup: bool = Query(False, description="Свернуть подкатегории в родительские категории"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> CategoryShareResponse:
    """Доли категорий в расходах или доходах за период."""
    return await AnalyticsViewSet.by_category(
        request=request,
        user=user,
        category_type=(CategoryType(transaction_type.value) if transaction_type else None),
        parent_id=parent_id,
        include_children=include_children,
        rollup=rollup,
        start_date=start_date,
        end_date=end_date,
        session_maker=session_maker,
    )


@analytics_router.get("/by-account", status_code=status.HTTP_200_OK, response_model=AccountShareResponse)
async def get_analytics_by_account(
    request: Request,
    user: CurrentUser,
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AccountShareResponse:
    """Обороты по счетам за период."""
    return await AnalyticsViewSet.by_account(
        request=request,
        user=user,
        start_date=start_date,
        end_date=end_date,
        session_maker=session_maker,
    )


@analytics_router.get("/matrix", status_code=status.HTTP_200_OK, response_model=MatrixResponse)
async def get_analytics_matrix(
    request: Request,
    user: CurrentUser,
    months: int = Query(6, ge=1, le=36, description="Сколько месяцев показать"),
    transaction_type: Optional[TransactionType] = Query(None, description="Тип записей"),
    rollup: bool = Query(True, description="Свернуть подкатегории в родительские категории"),
    end_date: Optional[datetime] = Query(None, description="Последний день отчёта"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> MatrixResponse:
    """Отчёт «категории × месяцы» для страницы аналитики."""
    return await AnalyticsViewSet.matrix(
        request=request,
        user=user,
        months=months,
        category_type=(CategoryType(transaction_type.value) if transaction_type else None),
        rollup=rollup,
        end_date=end_date,
        session_maker=session_maker,
    )
