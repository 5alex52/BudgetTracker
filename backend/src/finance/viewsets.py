from datetime import datetime
from typing import List
from typing import Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.database import get_async_session_maker
from src.users.schemas import User
from src.viewset import BaseViewSet
from src.viewset import check_permissions

from .models import AccountModel
from .models import CategoryModel
from .models import CurrencyModel
from .models import SubscriptionModel
from .models import TransactionModel
from .permissions import FinancePermission
from .schemas import AccountCreate
from .schemas import AccountSummary
from .schemas import AccountUpdate
from .schemas import BalanceOverview
from .schemas import CategoryCreate
from .schemas import CategoryNode
from .schemas import CategoryStat
from .schemas import CategoryType
from .schemas import CategoryUpdate
from .schemas import CurrencyCreate
from .schemas import CurrencyRate
from .schemas import CurrencyUpdate
from .schemas import SubscriptionCreate
from .schemas import SubscriptionUpdate
from .schemas import TransactionCreate
from .schemas import TransactionSummary
from .schemas import TransactionType
from .schemas import TransactionUpdate
from .schemas import TransactionWithDetails
from .service import AccountService
from .service import CategoryService
from .service import CurrencyService
from .service import SubscriptionService
from .service import TransactionService


class AccountViewSet(BaseViewSet[int, AccountCreate, AccountUpdate]):
    permission = FinancePermission
    service = AccountService

    @classmethod
    @check_permissions(action="list_accounts")
    async def list(
        cls,
        user: User,
        include_archived: bool = False,
        include_excluded: bool = True,
        offset: int = 0,
        limit: int = 100,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> List[AccountModel]:
        return await cls.service.get_list_by_user(
            user_id=user.id,
            include_archived=include_archived,
            include_excluded=include_excluded,
            offset=offset,
            limit=limit,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="retrieve_account")
    async def retrieve(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> AccountModel:
        return await cls.service.get_by_user(
            account_id=obj_id, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="create_account")
    async def create(
        cls,
        obj_data: AccountCreate,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> AccountModel:
        return await cls.service.create_for_user(
            schema=obj_data, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="update_account")
    async def update(
        cls,
        obj_id: int,
        obj_data: AccountUpdate,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> AccountModel:
        return await cls.service.update_for_user(
            account_id=obj_id,
            schema=obj_data,
            user_id=user.id,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="delete_account")
    async def delete(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> None:
        await cls.service.delete_for_user(
            account_id=obj_id, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="archive_account")
    async def archive(
        cls,
        obj_id: int,
        is_archived: bool,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> AccountModel:
        return await cls.service.set_archived(
            account_id=obj_id,
            user_id=user.id,
            is_archived=is_archived,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="exclude_account")
    async def exclude(
        cls,
        obj_id: int,
        is_excluded: bool,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> AccountModel:
        return await cls.service.set_excluded(
            account_id=obj_id,
            user_id=user.id,
            is_excluded=is_excluded,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="account_summary")
    async def summary(
        cls,
        obj_id: int,
        user: User,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> AccountSummary:
        return await cls.service.get_summary(
            account_id=obj_id,
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="accounts_balance")
    async def balance(
        cls,
        user: User,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> BalanceOverview:
        return await cls.service.get_balance_overview(
            user_id=user.id,
            end_date=end_date,
            session_maker=session_maker,
        )


class CategoryViewSet(BaseViewSet[int, CategoryCreate, CategoryUpdate]):
    permission = FinancePermission
    service = CategoryService

    @classmethod
    @check_permissions(action="list_categories")
    async def list(
        cls,
        user: User,
        category_type: Optional[CategoryType] = None,
        parent_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> List[CategoryModel]:
        return await cls.service.get_list_by_user(
            user_id=user.id,
            category_type=category_type,
            parent_id=parent_id,
            offset=offset,
            limit=limit,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="categories_tree")
    async def tree(
        cls,
        user: User,
        category_type: Optional[CategoryType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> List[CategoryNode]:
        return await cls.service.get_tree(
            user_id=user.id,
            category_type=category_type,
            start_date=start_date,
            end_date=end_date,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="categories_stats")
    async def stats(
        cls,
        user: User,
        category_type: Optional[CategoryType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> List[CategoryStat]:
        return await cls.service.get_stats(
            user_id=user.id,
            category_type=category_type,
            start_date=start_date,
            end_date=end_date,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="retrieve_category")
    async def retrieve(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> CategoryModel:
        return await cls.service.get_by_user(
            category_id=obj_id, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="create_category")
    async def create(
        cls,
        obj_data: CategoryCreate,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> CategoryModel:
        return await cls.service.create_for_user(
            schema=obj_data, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="update_category")
    async def update(
        cls,
        obj_id: int,
        obj_data: CategoryUpdate,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> CategoryModel:
        return await cls.service.update_for_user(
            category_id=obj_id,
            schema=obj_data,
            user_id=user.id,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="delete_category")
    async def delete(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> None:
        await cls.service.delete_for_user(
            category_id=obj_id, user_id=user.id, session_maker=session_maker
        )


class TransactionViewSet(BaseViewSet[int, TransactionCreate, TransactionUpdate]):
    permission = FinancePermission
    service = TransactionService

    @classmethod
    @check_permissions(action="list_transactions")
    async def list(
        cls,
        user: User,
        account_id: Optional[int] = None,
        category_id: Optional[int] = None,
        transaction_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        offset: int = 0,
        limit: int = 100,
        sort: str = "date_desc",
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **filters,
    ) -> List[TransactionWithDetails]:
        transactions = await cls.service.get_list_by_user(
            user_id=user.id,
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
        return [
            TransactionWithDetails.from_model(transaction)
            for transaction in transactions
        ]

    @classmethod
    @check_permissions(action="count_transactions")
    async def count(
        cls,
        user: User,
        account_id: Optional[int] = None,
        category_id: Optional[int] = None,
        transaction_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **filters,
    ) -> int:
        return await cls.service.count_by_user(
            user_id=user.id,
            account_id=account_id,
            category_id=category_id,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
            session_maker=session_maker,
            **filters,
        )

    @classmethod
    @check_permissions(action="bulk_delete_transactions")
    async def bulk_delete(
        cls,
        ids: List[int],
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> tuple:
        return await cls.service.bulk_delete(
            ids=ids, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="retrieve_transaction")
    async def retrieve(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> TransactionWithDetails:
        transaction = await cls.service.get_by_user(
            transaction_id=obj_id, user_id=user.id, session_maker=session_maker
        )
        return TransactionWithDetails.from_model(transaction)

    @classmethod
    @check_permissions(action="create_transaction")
    async def create(
        cls,
        obj_data: TransactionCreate,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> TransactionModel:
        return await cls.service.create_for_user(
            schema=obj_data, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="update_transaction")
    async def update(
        cls,
        obj_id: int,
        obj_data: TransactionUpdate,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> TransactionModel:
        return await cls.service.update_for_user(
            transaction_id=obj_id,
            schema=obj_data,
            user_id=user.id,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="delete_transaction")
    async def delete(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> None:
        await cls.service.delete_for_user(
            transaction_id=obj_id, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="transactions_summary")
    async def summary(
        cls,
        user: User,
        transaction_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> TransactionSummary:
        return await cls.service.get_summary(
            user_id=user.id,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
            session_maker=session_maker,
        )


class SubscriptionViewSet(BaseViewSet[int, SubscriptionCreate, SubscriptionUpdate]):
    permission = FinancePermission
    service = SubscriptionService

    @classmethod
    @check_permissions(action="list_subscriptions")
    async def list(
        cls,
        user: User,
        is_active: Optional[bool] = None,
        offset: int = 0,
        limit: int = 100,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> List[SubscriptionModel]:
        return await cls.service.get_list_by_user(
            user_id=user.id,
            is_active=is_active,
            offset=offset,
            limit=limit,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="retrieve_subscription")
    async def retrieve(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> SubscriptionModel:
        return await cls.service.get_by_user(
            subscription_id=obj_id, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="create_subscription")
    async def create(
        cls,
        obj_data: SubscriptionCreate,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> SubscriptionModel:
        return await cls.service.create_for_user(
            schema=obj_data, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="update_subscription")
    async def update(
        cls,
        obj_id: int,
        obj_data: SubscriptionUpdate,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> SubscriptionModel:
        return await cls.service.update_for_user(
            subscription_id=obj_id,
            schema=obj_data,
            user_id=user.id,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="delete_subscription")
    async def delete(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> None:
        await cls.service.delete_for_user(
            subscription_id=obj_id, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="upcoming_subscriptions")
    async def upcoming(
        cls,
        user: User,
        days: int = 7,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> List[SubscriptionModel]:
        return await cls.service.get_upcoming(
            user_id=user.id, days=days, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="advance_subscription")
    async def advance(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> SubscriptionModel:
        return await cls.service.advance_next_payment(
            subscription_id=obj_id, user_id=user.id, session_maker=session_maker
        )


class CurrencyViewSet(BaseViewSet[str, CurrencyCreate, CurrencyUpdate]):
    permission = FinancePermission
    service = CurrencyService

    @classmethod
    @check_permissions(action="list_currencies")
    async def list(
        cls,
        offset: int = 0,
        limit: int = 100,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> List[CurrencyModel]:
        return await cls.service.get_list(
            offset=offset, limit=limit, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="currency_rates")
    async def rates(
        cls,
        base: Optional[str] = None,
        user: Optional[User] = None,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> List[CurrencyRate]:
        """Catalog rates; for an authenticated user — with personal rates applied."""
        return await cls.service.get_rates(
            base=base, user_id=getattr(user, "id", None), session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="set_user_rate")
    async def set_rate(
        cls,
        code: str,
        rate: float,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> CurrencyRate:
        return await cls.service.set_user_rate(
            code=code, rate=rate, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="reset_user_rate")
    async def reset_rate(
        cls,
        code: str,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> None:
        await cls.service.reset_user_rate(
            code=code, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="retrieve_currency")
    async def retrieve(
        cls,
        obj_id: str,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> CurrencyModel:
        return await cls.service.get(code=obj_id, session_maker=session_maker)

    @classmethod
    @check_permissions(action="create_currency")
    async def create(
        cls,
        obj_data: CurrencyCreate,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> CurrencyModel:
        return await cls.service.create(schema=obj_data, session_maker=session_maker)

    @classmethod
    @check_permissions(action="update_currency")
    async def update(
        cls,
        obj_id: str,
        obj_data: CurrencyUpdate,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> CurrencyModel:
        return await cls.service.update(
            code=obj_id, schema=obj_data, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="delete_currency")
    async def delete(
        cls,
        obj_id: str,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> None:
        await cls.service.delete(code=obj_id, session_maker=session_maker)
