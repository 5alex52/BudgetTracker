"""Схемы аналитики: агрегаты «Обзора» и «Аналитики».

Модели данных живут в finance — здесь только представления ответов.
"""

from datetime import datetime
from typing import Any
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from src.finance.schemas import CategoryType


class PeriodTotals(BaseModel):
    """Итоги за период в базовой валюте."""

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    income: float = 0.0
    expense: float = 0.0
    net: float = 0.0
    transactions_count: int = 0


class PeriodChange(BaseModel):
    """Изменение в процентах к предыдущему периоду."""

    income: Optional[float] = None
    expense: Optional[float] = None
    net: Optional[float] = None


class AnalyticsSummary(PeriodTotals):
    """Итоги периода плюс сравнение с предыдущим таким же периодом."""

    previous: Optional[PeriodTotals] = None
    change: Optional[PeriodChange] = None


class SeriesPoint(BaseModel):
    """Точка графика денежного потока."""

    date: datetime
    income: float = 0.0
    expense: float = 0.0
    net: float = 0.0


class BalancePoint(BaseModel):
    """Точка графика остатка: сколько всего денег на конец интервала."""

    date: datetime
    value: float


class TimeseriesResponse(BaseModel):
    group_by: str
    metric: str
    points: List[Any] = Field(default_factory=list)


class CategoryShare(BaseModel):
    """Доля категории в расходах/доходах за период."""

    category_id: int
    name: str
    type: CategoryType
    parent_id: Optional[int] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    total: float
    share: float
    transactions_count: int


class CategoryShareResponse(BaseModel):
    items: List[CategoryShare] = Field(default_factory=list)
    total: float = 0.0


class AccountShare(BaseModel):
    """Обороты счёта за период."""

    account_id: int
    name: str
    currency_id: str
    income: float
    expense: float
    net: float
    transactions_count: int


class AccountShareResponse(BaseModel):
    items: List[AccountShare] = Field(default_factory=list)
    total: float = 0.0


class MatrixRow(BaseModel):
    """Строка отчёта «категории × месяцы»."""

    category_id: int
    name: str
    parent_id: Optional[int] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    values: List[float] = Field(default_factory=list)
    trends: List[Optional[float]] = Field(default_factory=list)


class MatrixResponse(BaseModel):
    months: List[str] = Field(default_factory=list)
    rows: List[MatrixRow] = Field(default_factory=list)
