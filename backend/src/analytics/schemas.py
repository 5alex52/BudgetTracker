"""Analytics schemas: aggregates for Overview and Analytics.

Data models live in finance — here we only have response representations.
"""

from datetime import datetime
from typing import Any
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from src.finance.schemas import CategoryType


class PeriodTotals(BaseModel):
    """Period totals in the base currency."""

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    income: float = 0.0
    expense: float = 0.0
    net: float = 0.0
    transactions_count: int = 0


class PeriodChange(BaseModel):
    """Percentage change compared to the previous period."""

    income: Optional[float] = None
    expense: Optional[float] = None
    net: Optional[float] = None


class AnalyticsSummary(PeriodTotals):
    """Period totals plus comparison to the previous period of the same length."""

    previous: Optional[PeriodTotals] = None
    change: Optional[PeriodChange] = None


class SeriesPoint(BaseModel):
    """Cash flow chart point."""

    date: datetime
    income: float = 0.0
    expense: float = 0.0
    net: float = 0.0


class BalancePoint(BaseModel):
    """Balance chart point: total amount of money at the end of the interval."""

    date: datetime
    value: float


class TimeseriesResponse(BaseModel):
    group_by: str
    metric: str
    points: List[Any] = Field(default_factory=list)


class CategoryShare(BaseModel):
    """Category share in expenses/income for the period."""

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
    """Account turnover for the period."""

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
    """Row of the "categories × months" report."""

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
