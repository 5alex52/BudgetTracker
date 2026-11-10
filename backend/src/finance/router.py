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
    include_archived: bool = Query(False, description="Include archived accounts"),
    include_excluded: bool = Query(
        True, description="Include accounts excluded from statistics"
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[AccountResponse]:
    """Accounts of the current user."""
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
    start_date: Optional[datetime] = Query(None, description="Start of the period"),
    end_date: Optional[datetime] = Query(
        None, description="End of the period: balance at this date"
    ),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> BalanceOverview:
    """Balance across all accounts in the base currency.

    If period boundaries are given, the balance is returned **as of the end of
    the period** (like a bank statement), not today's.
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
    """Account by ID."""
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
    """Create an account."""
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
    """Update an account."""
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
    is_archived: bool = Query(True, description="Archive or restore from archive"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AccountResponse:
    """Archive an account."""
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
        True, description="Exclude the account from statistics or restore it"
    ),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AccountResponse:
    """Exclude the account from statistics: the account and its records stay, but totals ignore them."""
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
    start_date: Optional[datetime] = Query(None, description="Start of the period"),
    end_date: Optional[datetime] = Query(None, description="End of the period"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AccountSummary:
    """Account turnover for the period — for the account card."""
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
    """Delete the account together with its transactions."""
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
    category_type: Optional[CategoryType] = Query(None, description="Category type"),
    parent_id: Optional[int] = Query(None, description="Parent category"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[CategoryResponse]:
    """Categories of the current user."""
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
    category_type: Optional[CategoryType] = Query(None, description="Category type"),
    start_date: Optional[datetime] = Query(
        None, description="Start of the period for counters"
    ),
    end_date: Optional[datetime] = Query(
        None, description="End of the period for counters"
    ),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[CategoryNode]:
    """Categories with subcategories and transaction counts."""
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
    category_type: Optional[CategoryType] = Query(None, description="Category type"),
    start_date: Optional[datetime] = Query(None, description="Start of the period"),
    end_date: Optional[datetime] = Query(None, description="End of the period"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[CategoryStat]:
    """How many records and what total amount each category has."""
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
    """Category by ID."""
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
    """Create a category."""
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
    """Update a category."""
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
    """Delete a category without transactions or subcategories."""
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
    """Collects multiple transaction list filters into one dict for the service."""
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
    account_id: Optional[int] = Query(None, description="Filter by account"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    transaction_type: Optional[TransactionType] = Query(
        None, description="Transaction type"
    ),
    account_ids: Optional[List[int]] = Query(
        None, description="Accounts (multiple selection)"
    ),
    category_ids: Optional[List[int]] = Query(
        None, description="Categories (multiple selection)"
    ),
    currency_ids: Optional[List[str]] = Query(
        None, description="Currencies (multiple selection)"
    ),
    types: Optional[List[TransactionType]] = Query(
        None, description="Record types (multiple selection)"
    ),
    q: Optional[str] = Query(
        None, max_length=100, description="Search by note, category and account"
    ),
    amount_min: Optional[float] = Query(None, ge=0, description="Amount from"),
    amount_max: Optional[float] = Query(None, ge=0, description="Amount to"),
    tag_ids: Optional[List[int]] = Query(None, description="Tags (multiple selection)"),
    start_date: Optional[datetime] = Query(None, description="Start of the period"),
    end_date: Optional[datetime] = Query(None, description="End of the period"),
    sort: str = Query(
        "date_desc",
        description="Sort: date_desc, date_asc, amount_desc, amount_asc",
    ),
    with_total: bool = Query(
        True, description="Return total number of records in the X-Total-Count header"
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[TransactionWithDetails]:
    """Transactions of the current user with account and category details."""
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
        # "Show more" and the counter in the list header need the total count under the same filters
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
    """Bulk delete records: account balances are rolled back, other users' records are not touched."""
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
        "csv", alias="format", pattern="^(csv|json)$", description="csv or json"
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
    """Export records for the period: CSV or JSON.

    Up to 5000 records are exported — enough for a year of active bookkeeping;
    the limit protects process memory from a "give me everything ever" request.
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
        None, description="Transaction type"
    ),
    start_date: Optional[datetime] = Query(None, description="Start of the period"),
    end_date: Optional[datetime] = Query(None, description="End of the period"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> TransactionSummary:
    """Summary by categories for the period."""
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
    """Transaction by ID: with account name, category and currency symbol."""
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
    """Create a transaction with account balance recalculation."""
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
    """Update a transaction with account balance recalculation."""
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
    """Delete a transaction with account balance rollback."""
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
        None, description="Filter by subscription activity"
    ),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[SubscriptionResponse]:
    """Subscriptions of the current user."""
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
    days: int = Query(7, ge=1, le=365, description="Planning horizon in days"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[SubscriptionResponse]:
    """Upcoming subscription payments."""
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
    """Subscription by ID."""
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
    """Create a subscription based on an existing transaction."""
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
    """Update a subscription."""
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
    """Advance the next payment date by one period."""
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
    """Delete a subscription."""
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
    """Currency catalog."""
    return await CurrencyViewSet.list(
        offset=offset, limit=limit, session_maker=session_maker
    )


@currencies_router.get(
    "/rates", status_code=status.HTTP_200_OK, response_model=List[CurrencyRate]
)
async def get_currency_rates(
    request: Request,
    base: Optional[str] = Query(
        None,
        min_length=3,
        max_length=3,
        description="Base currency (defaults to user's base currency)",
    ),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
    user: Optional[User] = Depends(get_current_active_user_optional),
) -> List[CurrencyRate]:
    """Currency rates relative to the chosen base: how many units per one base unit.

    The endpoint is public: the currency catalog is not personal data. If the
    user is authenticated, their personal rates (``is_custom``) are included in
    the response.
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
    """Personal currency rate: the user can count by their own bank's rate."""
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
    """Revert to the catalog rate."""
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
    """Currency by code."""
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
    """Add a currency to the catalog (superuser only)."""
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
    """Update a currency (superuser only)."""
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
    """Delete a currency from the catalog (superuser only)."""
    await CurrencyViewSet.delete(
        request=request, obj_id=code, user=user, session_maker=session_maker
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
