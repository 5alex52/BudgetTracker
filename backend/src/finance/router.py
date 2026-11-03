import csv
import io
import json
import logging
from datetime import datetime
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi import Response
from fastapi import status
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.database import get_async_session_maker
from src.users.dependencies import get_current_active_user_optional
from src.users.schemas import User

from .dependencies import CurrentUser
from .schemas import AccountCreate
from .schemas import AccountResponse
from .schemas import AccountSummary
from .schemas import AccountUpdate
from .schemas import BalanceOverview
from .schemas import BulkDeleteRequest
from .schemas import BulkDeleteResult
from .schemas import CategoryCreate
from .schemas import CategoryNode
from .schemas import CategoryResponse
from .schemas import CategoryStat
from .schemas import CategoryType
from .schemas import CategoryUpdate
from .schemas import CurrencyCreate
from .schemas import CurrencyRate
from .schemas import CurrencyResponse
from .schemas import CurrencyUpdate
from .schemas import SubscriptionCreate
from .schemas import SubscriptionResponse
from .schemas import SubscriptionUpdate
from .schemas import TransactionCreate
from .schemas import TransactionResponse
from .schemas import TransactionSummary
from .schemas import TransactionType
from .schemas import TransactionUpdate
from .schemas import TransactionWithDetails
from .schemas import UserCurrencyRateUpdate
from .viewsets import AccountViewSet
from .viewsets import CategoryViewSet
from .viewsets import CurrencyViewSet
from .viewsets import SubscriptionViewSet
from .viewsets import TransactionViewSet

logger = logging.getLogger(__name__)

accounts_router = APIRouter(prefix="/api/finance/accounts", tags=["Accounts"])
categories_router = APIRouter(prefix="/api/finance/categories", tags=["Categories"])
transactions_router = APIRouter(
    prefix="/api/finance/transactions", tags=["Transactions"]
)
subscriptions_router = APIRouter(
    prefix="/api/finance/subscriptions", tags=["Subscriptions"]
)
currencies_router = APIRouter(prefix="/api/finance/currencies", tags=["Currencies"])


@accounts_router.get(
    "/", status_code=status.HTTP_200_OK, response_model=List[AccountResponse]
)
async def get_accounts(
    request: Request,
    user: CurrentUser,
    include_archived: bool = Query(False, description="Включать архивированные счета"),
    include_excluded: bool = Query(
        True, description="Включать счета, исключённые из статистики"
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[AccountResponse]:
    """Счета текущего пользователя."""
    return await AccountViewSet.list(
        request=request,
        user=user,
        include_archived=include_archived,
        include_excluded=include_excluded,
        offset=offset,
        limit=limit,
        session_maker=session_maker,
    )


@accounts_router.get(
    "/balance", status_code=status.HTTP_200_OK, response_model=BalanceOverview
)
async def get_balance_overview(
    request: Request,
    user: CurrentUser,
    start_date: Optional[datetime] = Query(None, description="Начало периода"),
    end_date: Optional[datetime] = Query(
        None, description="Конец периода: остаток на эту дату"
    ),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> BalanceOverview:
    """Остаток по всем счетам в базовой валюте.

    Если переданы границы периода, отдаётся остаток **на конец периода**
    (как выписка в банке), а не сегодняшний.
    """
    return await AccountViewSet.balance(
        request=request,
        user=user,
        start_date=start_date,
        end_date=end_date,
        session_maker=session_maker,
    )


@accounts_router.get(
    "/{account_id}", status_code=status.HTTP_200_OK, response_model=AccountResponse
)
async def get_account(
    request: Request,
    account_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AccountResponse:
    """Счет по идентификатору."""
    return await AccountViewSet.retrieve(
        request=request, obj_id=account_id, user=user, session_maker=session_maker
    )


@accounts_router.post(
    "/", status_code=status.HTTP_201_CREATED, response_model=AccountResponse
)
async def create_account(
    request: Request,
    account_data: AccountCreate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AccountResponse:
    """Создание счета."""
    return await AccountViewSet.create(
        request=request, obj_data=account_data, user=user, session_maker=session_maker
    )


@accounts_router.patch(
    "/{account_id}", status_code=status.HTTP_200_OK, response_model=AccountResponse
)
async def update_account(
    request: Request,
    account_id: int,
    account_data: AccountUpdate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AccountResponse:
    """Обновление счета."""
    return await AccountViewSet.update(
        request=request,
        obj_id=account_id,
        obj_data=account_data,
        user=user,
        session_maker=session_maker,
    )


@accounts_router.post(
    "/{account_id}/archive",
    status_code=status.HTTP_200_OK,
    response_model=AccountResponse,
)
async def archive_account(
    request: Request,
    account_id: int,
    user: CurrentUser,
    is_archived: bool = Query(True, description="Архивировать или вернуть из архива"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AccountResponse:
    """Архивация счета."""
    return await AccountViewSet.archive(
        request=request,
        obj_id=account_id,
        is_archived=is_archived,
        user=user,
        session_maker=session_maker,
    )


@accounts_router.post(
    "/{account_id}/exclude",
    status_code=status.HTTP_200_OK,
    response_model=AccountResponse,
)
async def exclude_account(
    request: Request,
    account_id: int,
    user: CurrentUser,
    is_excluded: bool = Query(
        True, description="Исключить счёт из статистики или вернуть обратно"
    ),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AccountResponse:
    """Исключение счёта из статистики: счёт и записи остаются, итоги их не учитывают."""
    return await AccountViewSet.exclude(
        request=request,
        obj_id=account_id,
        is_excluded=is_excluded,
        user=user,
        session_maker=session_maker,
    )


@accounts_router.get(
    "/{account_id}/summary",
    status_code=status.HTTP_200_OK,
    response_model=AccountSummary,
)
async def get_account_summary(
    request: Request,
    account_id: int,
    user: CurrentUser,
    start_date: Optional[datetime] = Query(None, description="Начало периода"),
    end_date: Optional[datetime] = Query(None, description="Конец периода"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AccountSummary:
    """Обороты по счёту за период — для карточки счёта."""
    return await AccountViewSet.summary(
        request=request,
        obj_id=account_id,
        start_date=start_date,
        end_date=end_date,
        user=user,
        session_maker=session_maker,
    )


@accounts_router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    request: Request,
    account_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    """Удаление счета вместе с его транзакциями."""
    await AccountViewSet.delete(
        request=request, obj_id=account_id, user=user, session_maker=session_maker
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@categories_router.get(
    "/", status_code=status.HTTP_200_OK, response_model=List[CategoryResponse]
)
async def get_categories(
    request: Request,
    user: CurrentUser,
    category_type: Optional[CategoryType] = Query(None, description="Тип категории"),
    parent_id: Optional[int] = Query(None, description="Родительская категория"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[CategoryResponse]:
    """Категории текущего пользователя."""
    return await CategoryViewSet.list(
        request=request,
        user=user,
        category_type=category_type,
        parent_id=parent_id,
        offset=offset,
        limit=limit,
        session_maker=session_maker,
    )


@categories_router.get(
    "/tree", status_code=status.HTTP_200_OK, response_model=List[CategoryNode]
)
async def get_categories_tree(
    request: Request,
    user: CurrentUser,
    category_type: Optional[CategoryType] = Query(None, description="Тип категории"),
    start_date: Optional[datetime] = Query(
        None, description="Начало периода для счётчиков"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Конец периода для счётчиков"
    ),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[CategoryNode]:
    """Категории с подкатегориями и количеством записей."""
    return await CategoryViewSet.tree(
        request=request,
        user=user,
        category_type=category_type,
        start_date=start_date,
        end_date=end_date,
        session_maker=session_maker,
    )


@categories_router.get(
    "/stats", status_code=status.HTTP_200_OK, response_model=List[CategoryStat]
)
async def get_categories_stats(
    request: Request,
    user: CurrentUser,
    category_type: Optional[CategoryType] = Query(None, description="Тип категории"),
    start_date: Optional[datetime] = Query(None, description="Начало периода"),
    end_date: Optional[datetime] = Query(None, description="Конец периода"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[CategoryStat]:
    """Сколько записей и на какую сумму приходится на каждую категорию."""
    return await CategoryViewSet.stats(
        request=request,
        user=user,
        category_type=category_type,
        start_date=start_date,
        end_date=end_date,
        session_maker=session_maker,
    )


@categories_router.get(
    "/{category_id}", status_code=status.HTTP_200_OK, response_model=CategoryResponse
)
async def get_category(
    request: Request,
    category_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> CategoryResponse:
    """Категория по идентификатору."""
    return await CategoryViewSet.retrieve(
        request=request, obj_id=category_id, user=user, session_maker=session_maker
    )


@categories_router.post(
    "/", status_code=status.HTTP_201_CREATED, response_model=CategoryResponse
)
async def create_category(
    request: Request,
    category_data: CategoryCreate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> CategoryResponse:
    """Создание категории."""
    return await CategoryViewSet.create(
        request=request, obj_data=category_data, user=user, session_maker=session_maker
    )


@categories_router.patch(
    "/{category_id}", status_code=status.HTTP_200_OK, response_model=CategoryResponse
)
async def update_category(
    request: Request,
    category_id: int,
    category_data: CategoryUpdate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> CategoryResponse:
    """Обновление категории."""
    return await CategoryViewSet.update(
        request=request,
        obj_id=category_id,
        obj_data=category_data,
        user=user,
        session_maker=session_maker,
    )


@categories_router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    request: Request,
    category_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    """Удаление категории без транзакций и подкатегорий."""
    await CategoryViewSet.delete(
        request=request, obj_id=category_id, user=user, session_maker=session_maker
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _transaction_filters(
    account_ids: Optional[List[int]],
    category_ids: Optional[List[int]],
    currency_ids: Optional[List[str]],
    types: Optional[List[TransactionType]],
    query: Optional[str],
    amount_min: Optional[float],
    amount_max: Optional[float],
    tag_ids: Optional[List[int]] = None,
) -> dict:
    """Собирает множественные фильтры списка записей в один словарь для сервиса."""
    return {
        "account_ids": account_ids,
        "category_ids": category_ids,
        "currency_ids": (
            [code.upper() for code in currency_ids] if currency_ids else None
        ),
        "transaction_types": types,
        "query": query,
        "amount_min": amount_min,
        "amount_max": amount_max,
        "tag_ids": tag_ids,
    }


@transactions_router.get(
    "/", status_code=status.HTTP_200_OK, response_model=List[TransactionWithDetails]
)
async def get_transactions(
    request: Request,
    response: Response,
    user: CurrentUser,
    account_id: Optional[int] = Query(None, description="Фильтр по счету"),
    category_id: Optional[int] = Query(None, description="Фильтр по категории"),
    transaction_type: Optional[TransactionType] = Query(
        None, description="Тип транзакции"
    ),
    account_ids: Optional[List[int]] = Query(
        None, description="Счета (множественный выбор)"
    ),
    category_ids: Optional[List[int]] = Query(
        None, description="Категории (множественный выбор)"
    ),
    currency_ids: Optional[List[str]] = Query(
        None, description="Валюты (множественный выбор)"
    ),
    types: Optional[List[TransactionType]] = Query(
        None, description="Типы записей (множественный выбор)"
    ),
    q: Optional[str] = Query(
        None, max_length=100, description="Поиск по заметке, категории и счёту"
    ),
    amount_min: Optional[float] = Query(None, ge=0, description="Сумма от"),
    amount_max: Optional[float] = Query(None, ge=0, description="Сумма до"),
    tag_ids: Optional[List[int]] = Query(
        None, description="Метки (множественный выбор)"
    ),
    start_date: Optional[datetime] = Query(None, description="Начало периода"),
    end_date: Optional[datetime] = Query(None, description="Конец периода"),
    sort: str = Query(
        "date_desc",
        description="Сортировка: date_desc, date_asc, amount_desc, amount_asc",
    ),
    with_total: bool = Query(
        True, description="Отдать общее количество записей в заголовке X-Total-Count"
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[TransactionWithDetails]:
    """Транзакции текущего пользователя с деталями по счету и категории."""
    filters = _transaction_filters(
        account_ids,
        category_ids,
        currency_ids,
        types,
        q,
        amount_min,
        amount_max,
        tag_ids,
    )
    if sort not in {"date_desc", "date_asc", "amount_desc", "amount_asc"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown sort option"
        )

    transactions = await TransactionViewSet.list(
        request=request,
        user=user,
        account_id=account_id,
        category_id=category_id,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date,
        offset=offset,
        limit=limit,
        sort=sort,
        session_maker=session_maker,
        **filters,
    )
    if with_total:
        # «Показать ещё» и счётчик в шапке списка требуют общего количества под теми же фильтрами
        total = await TransactionViewSet.count(
            request=request,
            user=user,
            account_id=account_id,
            category_id=category_id,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
            session_maker=session_maker,
            **filters,
        )
        response.headers["X-Total-Count"] = str(total)
        response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    return transactions


@transactions_router.post(
    "/bulk-delete", status_code=status.HTTP_200_OK, response_model=BulkDeleteResult
)
async def bulk_delete_transactions(
    request: Request,
    payload: BulkDeleteRequest,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> BulkDeleteResult:
    """Массовое удаление записей: балансы счетов откатываются, чужие записи не трогаются."""
    deleted, missing = await TransactionViewSet.bulk_delete(
        request=request,
        ids=payload.ids,
        user=user,
        session_maker=session_maker,
    )
    return BulkDeleteResult(deleted=deleted, missing=missing)


@transactions_router.get("/export", status_code=status.HTTP_200_OK)
async def export_transactions(
    request: Request,
    user: CurrentUser,
    export_format: str = Query(
        "csv", alias="format", pattern="^(csv|json)$", description="csv или json"
    ),
    account_ids: Optional[List[int]] = Query(None),
    category_ids: Optional[List[int]] = Query(None),
    currency_ids: Optional[List[str]] = Query(None),
    types: Optional[List[TransactionType]] = Query(None),
    q: Optional[str] = Query(None, max_length=100),
    amount_min: Optional[float] = Query(None, ge=0),
    amount_max: Optional[float] = Query(None, ge=0),
    tag_ids: Optional[List[int]] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    """Выгрузка записей за период: CSV или JSON.

    Выгружается до 5000 записей — этого хватает на год активного учёта;
    ограничение защищает память процесса от запроса «отдай всё за всё время».
    """
    filters = _transaction_filters(
        account_ids,
        category_ids,
        currency_ids,
        types,
        q,
        amount_min,
        amount_max,
        tag_ids,
    )
    transactions = await TransactionViewSet.list(
        request=request,
        user=user,
        start_date=start_date,
        end_date=end_date,
        offset=0,
        limit=5000,
        session_maker=session_maker,
        **filters,
    )
    stamp = datetime.now().strftime("%Y%m%d-%H%M")

    if export_format == "json":
        payload = json.dumps(
            [transaction.model_dump(mode="json") for transaction in transactions],
            ensure_ascii=False,
        )
        return Response(
            content=payload,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="transactions-{stamp}.json"'
            },
        )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["date", "type", "account", "category", "amount", "currency", "note"]
    )
    for transaction in transactions:
        writer.writerow(
            [
                transaction.date.strftime("%Y-%m-%d %H:%M"),
                (
                    transaction.type.value
                    if hasattr(transaction.type, "value")
                    else transaction.type
                ),
                transaction.account_name,
                transaction.category_name,
                transaction.amount,
                transaction.currency_id,
                (transaction.note or "").replace("\n", " "),
            ]
        )
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="transactions-{stamp}.csv"'
        },
    )


@transactions_router.get(
    "/summary", status_code=status.HTTP_200_OK, response_model=TransactionSummary
)
async def get_transactions_summary(
    request: Request,
    user: CurrentUser,
    transaction_type: Optional[TransactionType] = Query(
        None, description="Тип транзакции"
    ),
    start_date: Optional[datetime] = Query(None, description="Начало периода"),
    end_date: Optional[datetime] = Query(None, description="Конец периода"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> TransactionSummary:
    """Сводка по категориям за период."""
    return await TransactionViewSet.summary(
        request=request,
        user=user,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date,
        session_maker=session_maker,
    )


@transactions_router.get(
    "/{transaction_id}",
    status_code=status.HTTP_200_OK,
    response_model=TransactionWithDetails,
)
async def get_transaction(
    request: Request,
    transaction_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> TransactionResponse:
    """Транзакция по идентификатору: с именем счёта, категорией и символом валюты."""
    return await TransactionViewSet.retrieve(
        request=request, obj_id=transaction_id, user=user, session_maker=session_maker
    )


@transactions_router.post(
    "/", status_code=status.HTTP_201_CREATED, response_model=TransactionResponse
)
async def create_transaction(
    request: Request,
    transaction_data: TransactionCreate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> TransactionResponse:
    """Создание транзакции с пересчетом баланса счета."""
    return await TransactionViewSet.create(
        request=request,
        obj_data=transaction_data,
        user=user,
        session_maker=session_maker,
    )


@transactions_router.patch(
    "/{transaction_id}",
    status_code=status.HTTP_200_OK,
    response_model=TransactionResponse,
)
async def update_transaction(
    request: Request,
    transaction_id: int,
    transaction_data: TransactionUpdate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> TransactionResponse:
    """Обновление транзакции с пересчетом баланса счета."""
    return await TransactionViewSet.update(
        request=request,
        obj_id=transaction_id,
        obj_data=transaction_data,
        user=user,
        session_maker=session_maker,
    )


@transactions_router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    request: Request,
    transaction_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    """Удаление транзакции с откатом баланса счета."""
    await TransactionViewSet.delete(
        request=request, obj_id=transaction_id, user=user, session_maker=session_maker
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@subscriptions_router.get(
    "/", status_code=status.HTTP_200_OK, response_model=List[SubscriptionResponse]
)
async def get_subscriptions(
    request: Request,
    user: CurrentUser,
    is_active: Optional[bool] = Query(
        None, description="Фильтр по активности подписки"
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[SubscriptionResponse]:
    """Подписки текущего пользователя."""
    return await SubscriptionViewSet.list(
        request=request,
        user=user,
        is_active=is_active,
        offset=offset,
        limit=limit,
        session_maker=session_maker,
    )


@subscriptions_router.get(
    "/upcoming",
    status_code=status.HTTP_200_OK,
    response_model=List[SubscriptionResponse],
)
async def get_upcoming_subscriptions(
    request: Request,
    user: CurrentUser,
    days: int = Query(7, ge=1, le=365, description="Горизонт планирования в днях"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[SubscriptionResponse]:
    """Ближайшие платежи по подпискам."""
    return await SubscriptionViewSet.upcoming(
        request=request, user=user, days=days, session_maker=session_maker
    )


@subscriptions_router.get(
    "/{subscription_id}",
    status_code=status.HTTP_200_OK,
    response_model=SubscriptionResponse,
)
async def get_subscription(
    request: Request,
    subscription_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> SubscriptionResponse:
    """Подписка по идентификатору."""
    return await SubscriptionViewSet.retrieve(
        request=request, obj_id=subscription_id, user=user, session_maker=session_maker
    )


@subscriptions_router.post(
    "/", status_code=status.HTTP_201_CREATED, response_model=SubscriptionResponse
)
async def create_subscription(
    request: Request,
    subscription_data: SubscriptionCreate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> SubscriptionResponse:
    """Оформление подписки на основе существующей транзакции."""
    return await SubscriptionViewSet.create(
        request=request,
        obj_data=subscription_data,
        user=user,
        session_maker=session_maker,
    )


@subscriptions_router.patch(
    "/{subscription_id}",
    status_code=status.HTTP_200_OK,
    response_model=SubscriptionResponse,
)
async def update_subscription(
    request: Request,
    subscription_id: int,
    subscription_data: SubscriptionUpdate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> SubscriptionResponse:
    """Обновление подписки."""
    return await SubscriptionViewSet.update(
        request=request,
        obj_id=subscription_id,
        obj_data=subscription_data,
        user=user,
        session_maker=session_maker,
    )


@subscriptions_router.post(
    "/{subscription_id}/advance",
    status_code=status.HTTP_200_OK,
    response_model=SubscriptionResponse,
)
async def advance_subscription(
    request: Request,
    subscription_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> SubscriptionResponse:
    """Перенос даты следующего платежа на один период вперед."""
    return await SubscriptionViewSet.advance(
        request=request, obj_id=subscription_id, user=user, session_maker=session_maker
    )


@subscriptions_router.delete(
    "/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_subscription(
    request: Request,
    subscription_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    """Удаление подписки."""
    await SubscriptionViewSet.delete(
        request=request, obj_id=subscription_id, user=user, session_maker=session_maker
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@currencies_router.get(
    "/", status_code=status.HTTP_200_OK, response_model=List[CurrencyResponse]
)
async def get_currencies(
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[CurrencyResponse]:
    """Справочник валют."""
    return await CurrencyViewSet.list(
        offset=offset, limit=limit, session_maker=session_maker
    )


@currencies_router.get(
    "/rates", status_code=status.HTTP_200_OK, response_model=List[CurrencyRate]
)
async def get_currency_rates(
    request: Request,
    base: str = Query("BYN", min_length=3, max_length=3, description="Базовая валюта"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
    user: Optional[User] = Depends(get_current_active_user_optional),
) -> List[CurrencyRate]:
    """Курсы валют относительно выбранной базовой: сколько единиц за одну базовую.

    Эндпоинт публичный: справочник курсов не является личными данными. Если
    пользователь авторизован, в ответ попадают его личные курсы (``is_custom``).
    """
    return await CurrencyViewSet.rates(
        request=request, base=base, user=user, session_maker=session_maker
    )


@currencies_router.put(
    "/{code}/rate", status_code=status.HTTP_200_OK, response_model=CurrencyRate
)
async def set_user_currency_rate(
    request: Request,
    code: str,
    payload: UserCurrencyRateUpdate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> CurrencyRate:
    """Личный курс валюты: пользователь может считать по курсу своего банка."""
    return await CurrencyViewSet.set_rate(
        request=request,
        code=code,
        rate=payload.rate,
        user=user,
        session_maker=session_maker,
    )


@currencies_router.delete("/{code}/rate", status_code=status.HTTP_204_NO_CONTENT)
async def reset_user_currency_rate(
    request: Request,
    code: str,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> None:
    """Возврат к курсу справочника."""
    await CurrencyViewSet.reset_rate(
        request=request, code=code, user=user, session_maker=session_maker
    )


@currencies_router.get(
    "/{code}", status_code=status.HTTP_200_OK, response_model=CurrencyResponse
)
async def get_currency(
    code: str,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> CurrencyResponse:
    """Валюта по коду."""
    return await CurrencyViewSet.retrieve(obj_id=code, session_maker=session_maker)


@currencies_router.post(
    "/", status_code=status.HTTP_201_CREATED, response_model=CurrencyResponse
)
async def create_currency(
    request: Request,
    currency_data: CurrencyCreate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> CurrencyResponse:
    """Добавление валюты в справочник (только суперпользователь)."""
    return await CurrencyViewSet.create(
        request=request, obj_data=currency_data, user=user, session_maker=session_maker
    )


@currencies_router.patch(
    "/{code}", status_code=status.HTTP_200_OK, response_model=CurrencyResponse
)
async def update_currency(
    request: Request,
    code: str,
    currency_data: CurrencyUpdate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> CurrencyResponse:
    """Обновление валюты (только суперпользователь)."""
    return await CurrencyViewSet.update(
        request=request,
        obj_id=code,
        obj_data=currency_data,
        user=user,
        session_maker=session_maker,
    )


@currencies_router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_currency(
    request: Request,
    code: str,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    """Удаление валюты из справочника (только суперпользователь)."""
    await CurrencyViewSet.delete(
        request=request, obj_id=code, user=user, session_maker=session_maker
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
