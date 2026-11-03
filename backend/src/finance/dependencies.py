from datetime import datetime
from typing import Annotated
from typing import Optional

from fastapi import Depends
from fastapi import Query
from pydantic import BaseModel
from pydantic import ConfigDict
from src.users.dependencies import get_current_active_user
from src.users.schemas import User

from .schemas import TransactionType

CurrentUser = Annotated[User, Depends(get_current_active_user)]


class PaginationParams(BaseModel):
    offset: int = 0
    limit: int = 100

    model_config = ConfigDict(from_attributes=True)


class TransactionFilters(BaseModel):
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    transaction_type: Optional[TransactionType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


def get_pagination(
    offset: int = Query(0, ge=0, description="Сколько записей пропустить"),
    limit: int = Query(
        100, ge=1, le=500, description="Максимальное количество записей"
    ),
) -> PaginationParams:
    """Pagination dependency."""
    return PaginationParams(offset=offset, limit=limit)


def get_transaction_filters(
    account_id: Optional[int] = Query(None, description="Фильтр по счету"),
    category_id: Optional[int] = Query(None, description="Фильтр по категории"),
    transaction_type: Optional[TransactionType] = Query(
        None, description="Тип транзакции"
    ),
    start_date: Optional[datetime] = Query(None, description="Начало периода"),
    end_date: Optional[datetime] = Query(None, description="Конец периода"),
) -> TransactionFilters:
    """Filtering dependency for the transaction list."""
    return TransactionFilters(
        account_id=account_id,
        category_id=category_id,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date,
    )


Pagination = Annotated[PaginationParams, Depends(get_pagination)]
Filters = Annotated[TransactionFilters, Depends(get_transaction_filters)]
