import csv
import io
import json
import logging
from datetime import datetime
from datetime import timedelta
from typing import List
from typing import Optional

from fastapi import HTTPException
from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import async_session_maker
from ..service import BaseService
from .dao import AccountDAO
from .dao import CategoryDAO
from .dao import CurrencyDAO
from .dao import SubscriptionDAO
from .dao import TransactionDAO
from .dao import UserCurrencyRateDAO
from .models import AccountModel
from .models import CategoryModel
from .models import CurrencyModel
from .models import SubscriptionModel
from .models import TransactionModel
from .models import UserCurrencyRateModel
from .schemas import AccountCreate
from .schemas import AccountSummary
from .schemas import AccountType
from .schemas import AccountUpdate
from .schemas import BalanceOverview
from .schemas import BalanceOverviewAccount
from .schemas import CategoryCreate
from .schemas import CategoryNode
from .schemas import CategoryStat
from .schemas import CategoryTotal
from .schemas import CategoryType
from .schemas import CategoryUpdate
from .schemas import CurrencyCreate
from .schemas import CurrencyRate
from .schemas import CurrencyUpdate
from .schemas import SubscriptionCreate
from .schemas import SubscriptionUpdate
from .schemas import TransactionCreate
from .schemas import TransactionImportRequest
from .schemas import TransactionImportResult
from .schemas import TransactionSummary
from .schemas import TransactionType
from .schemas import TransactionUpdate
from .tags import attach_tags
from .tags import ensure_tags_owned
from .utils import balance_delta
from .utils import calculate_next_payment_date
from .utils import convert_amount
from .utils import normalize_period

logger = logging.getLogger(__name__)


def _resolve_session_maker(
    session_maker: Optional[async_sessionmaker],
) -> async_sessionmaker:
    return session_maker or async_session_maker


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


async def _get_owned_account(session: AsyncSession, account_id: int, user_id) -> AccountModel:
    """Returns an account owned by the user or raises 404."""
    account = await AccountDAO.find_one_by_user(session, account_id, user_id)
    if account is None:
        raise _not_found("Account not found")
    return account


def _ensure_not_crypto(account: AccountModel) -> None:
    """A crypto wallet-account's balance is owned by sync: transactions must not touch it."""
    if account.crypto_kind is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Crypto wallet accounts are managed from the crypto page",
        )


async def _get_owned_category(session: AsyncSession, category_id: int, user_id) -> CategoryModel:
    """Returns a category owned by the user or raises 404."""
    category = await CategoryDAO.find_one_by_user(session, category_id, user_id)
    if category is None:
        raise _not_found("Category not found")
    return category


async def _get_currency(session: AsyncSession, code: str) -> CurrencyModel:
    """Returns a currency from the global catalog or raises 400."""
    code = (code or "").upper()
    currency = await CurrencyDAO.find_one_or_none(session, code=code)
    if currency is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown currency: {code}")
    return currency


async def _resolve_base_rate(session: AsyncSession, user_id) -> float:
    """How many base units one unit of the base currency is worth.

    Every aggregate is expressed in the user's *own* base currency
    (``UserModel.base_currency``), which is not necessarily the catalog base
    (USD). The catalog stores "how many USD one unit costs", so converting a
    catalog rate into the user's base means dividing by the base's own rate.
    Personal overrides (``user_currency_rates``) win over the catalog.
    """
    from ..users.models import UserModel

    user = await session.get(UserModel, user_id)
    base = (getattr(user, "base_currency", None) or "USD").upper()
    currency = await CurrencyDAO.find_one_or_none(session, code=base)
    if currency is None:
        base = "USD"
        currency = await CurrencyDAO.find_one_or_none(session, code=base)
    if currency is None:
        return 1.0
    override = await UserCurrencyRateDAO.find_one(session, user_id, base)
    rate = override.rate if override is not None else currency.exchange_rate_to_base
    return float(rate) if rate and rate > 0 else 1.0


async def _resolve_base_code(session: AsyncSession, user_id) -> str:
    """User's base currency code (uppercased)."""
    from ..users.models import UserModel

    user = await session.get(UserModel, user_id)
    base = (getattr(user, "base_currency", None) or "USD").upper()
    currency = await CurrencyDAO.find_one_or_none(session, code=base)
    return base if currency is not None else "USD"


def _validate_category_type(category: CategoryModel, transaction_type: TransactionType) -> None:
    """A transaction may only use a category of the matching type."""
    if category.type != CategoryType(transaction_type.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category type does not match transaction type",
        )


def _converted_delta(
    transaction_type: TransactionType,
    amount: float,
    transaction_rate: float,
    account_rate: float,
) -> float:
    """Transaction effect on the balance expressed in the account currency."""
    amount_in_account_currency = convert_amount(amount, transaction_rate, account_rate)
    return balance_delta(transaction_type, amount_in_account_currency)


async def _transfer_category(session: AsyncSession, user_id) -> CategoryModel:
    """Transfer category: transfers have no user-facing category.

    The ``transactions.category_id`` column is required, so a transfer needs one
    neutral category. We reuse the first existing transfer category if any,
    otherwise create it on the first transfer.
    """
    existing = await CategoryDAO.find_all_by_user(session, user_id, category_type=CategoryType.TRANSFER, limit=1)
    if existing:
        return existing[0]
    created = await CategoryDAO.create(
        session,
        {
            "name": "Перевод",
            "type": CategoryType.TRANSFER,
            "parent_id": None,
            "icon": "arrow-left-right",
            "color": "#5b8fd6",
            "user_id": user_id,
        },
    )
    if created is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Transfer category creation conflict",
        )
    await _invalidate_categories()
    return created


async def _resolve_transfer_account(
    session: AsyncSession,
    user_id,
    source_account_id: int,
    transfer_account_id: Optional[int],
    currency_id: str,
    session_maker: Optional[async_sessionmaker] = None,
) -> AccountModel:
    """Transfer destination account: owned, different from source, writable."""
    if transfer_account_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transfer account is required",
        )
    if int(transfer_account_id) == int(source_account_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transfer accounts must differ",
        )
    account = await _get_owned_account(session, transfer_account_id, user_id)
    return account


class CurrencyService(BaseService[CurrencyModel, CurrencyCreate, CurrencyUpdate]):
    dao = CurrencyDAO

    @classmethod
    async def _user_base_currency(cls, session_maker: Optional[async_sessionmaker], user_id) -> str:
        """User's base currency code; falls back to "USD" when not configured."""
        from ..users.models import UserModel

        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            user = await session.get(UserModel, user_id)
            return (getattr(user, "base_currency", None) or "USD").upper()

    @classmethod
    async def get_list(
        cls,
        offset: int = 0,
        limit: int = 100,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> List[CurrencyModel]:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            return await cls.dao.find_all_ordered(session, offset=offset, limit=limit)

    @classmethod
    async def get(cls, code: str, session_maker: Optional[async_sessionmaker] = None) -> CurrencyModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            currency = await cls.dao.find_one_or_none(session, code=code)
        if currency is None:
            raise _not_found("Currency not found")
        return currency

    @classmethod
    async def get_rates(
        cls,
        base: Optional[str] = None,
        user_id=None,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> List[CurrencyRate]:
        # Base currency is a personal user setting; "USD" is the fallback for
        # anonymous catalog requests.
        if base is None and user_id is not None:
            base = await CurrencyService._user_base_currency(session_maker, user_id)
        base = (base or "USD").upper()
        """Exchange rates of all currencies relative to the chosen base.

        The catalog stores "how many base units one currency unit costs", but the
        Currencies screen shows the inverse — "how many currency units per one
        base unit" — so the rate is flipped via the base currency.
        """
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            currencies = await cls.dao.find_all_ordered(session, limit=500)
            # Personal rates override the catalog: user may count by their own bank
            overrides = {}
            if user_id is not None:
                rows = await UserCurrencyRateDAO.find_all_by_user(session, user_id)
                overrides = {row.code: row.rate for row in rows}
        base_currency = next((item for item in currencies if item.code == base), None)
        if base_currency is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown currency: {base}",
            )
        base_rate = overrides.get(base_currency.code, base_currency.exchange_rate_to_base)
        if base_rate <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid exchange rate")
        rates = []
        for currency in currencies:
            rate_to_base = overrides.get(currency.code, currency.exchange_rate_to_base)
            rates.append(
                CurrencyRate(
                    code=currency.code,
                    name=currency.name,
                    symbol=currency.symbol,
                    rate=round(base_rate / rate_to_base, 6) if rate_to_base else 0.0,
                    is_base=currency.code == base_currency.code,
                    is_custom=currency.code in overrides,
                )
            )
        return rates

    @classmethod
    async def set_user_rate(
        cls,
        code: str,
        rate: float,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> CurrencyRate:
        """Personal currency rate: how many base units one unit of the currency costs."""
        if rate <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rate must be positive")
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            currency = await cls.dao.find_one_or_none(session, code=code.upper())
            if currency is None:
                raise _not_found("Currency not found")
            existing = await UserCurrencyRateDAO.find_one(session, user_id, code)
            if existing is None:
                session.add(UserCurrencyRateModel(user_id=user_id, code=currency.code, rate=rate))
            else:
                existing.rate = rate
            await session.commit()
        return CurrencyRate(
            code=currency.code,
            name=currency.name,
            symbol=currency.symbol,
            rate=rate,
            is_base=False,
            is_custom=True,
        )

    @classmethod
    async def reset_user_rate(cls, code: str, user_id, session_maker: Optional[async_sessionmaker] = None) -> None:
        """Revert to the catalog rate."""
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            existing = await UserCurrencyRateDAO.find_one(session, user_id, code)
            if existing is None:
                raise _not_found("Custom rate not found")
            await session.delete(existing)
            await session.commit()

    @classmethod
    async def update(
        cls,
        code: str,
        schema: CurrencyUpdate,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> CurrencyModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            currency = await cls.dao.find_one_or_none(session, code=code)
            if currency is None:
                raise _not_found("Currency not found")
            for field, value in schema.model_dump(exclude_unset=True).items():
                setattr(currency, field, value)
            await session.commit()
        return currency

    @classmethod
    async def delete(cls, code: str, session_maker: Optional[async_sessionmaker] = None) -> None:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            try:
                await cls.dao.delete(session, CurrencyModel.code == code)
                await session.commit()
            except ValueError:
                raise _not_found("Currency not found")
            except SQLAlchemyError:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Currency is used by existing accounts or transactions",
                )


async def _invalidate_analytics() -> None:
    """Invalidate the analytics cache: Overview numbers depend on records and accounts."""
    from ..cache import Cache

    await Cache.delete_scope("analytics")


async def _invalidate_categories() -> None:
    """Invalidate the categories cache: the tree and list change on any mutation."""
    from ..cache import Cache

    await Cache.delete_scope("categories")


async def _effective_currency_rate(session: AsyncSession, user_id, code: str) -> float:
    """Currency rate with the user's personal override applied."""
    currency = await _get_currency(session, code)
    override = await UserCurrencyRateDAO.find_one(session, user_id, currency.code)
    rate = override.rate if override is not None else currency.exchange_rate_to_base
    return float(rate) if rate and rate > 0 else 1.0


class AccountService(BaseService[AccountModel, AccountCreate, AccountUpdate]):
    dao = AccountDAO

    @classmethod
    async def get_list_by_user(
        cls,
        user_id,
        include_archived: bool = False,
        include_excluded: bool = True,
        offset: int = 0,
        limit: int = 100,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> List[AccountModel]:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            accounts = await cls.dao.find_all_by_user(
                session,
                user_id,
                include_archived=include_archived,
                include_excluded=include_excluded,
                offset=offset,
                limit=limit,
            )
            return accounts

    @classmethod
    async def get_by_user(
        cls,
        account_id: int,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> AccountModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            account = await _get_owned_account(session, account_id, user_id)
            return account

    @classmethod
    async def create_for_user(
        cls,
        schema: AccountCreate,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> AccountModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            await _get_currency(session, schema.currency_id)
            account = await cls.dao.create(session, {**schema.model_dump(), "user_id": user_id})
            if account is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Account creation conflict",
                )
            await session.commit()
        await _invalidate_analytics()
        return account

    @classmethod
    async def update_for_user(
        cls,
        account_id: int,
        schema: AccountUpdate,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> AccountModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            account = await _get_owned_account(session, account_id, user_id)
            update_data = schema.model_dump(exclude_unset=True)
            if account.crypto_kind is not None and {"balance", "type", "currency_id"} & set(update_data):
                # These fields of a wallet-account belong to the crypto page/sync
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Crypto wallet accounts are managed from the crypto page",
                )
            if "currency_id" in update_data:
                await _get_currency(session, update_data["currency_id"])
            for field, value in update_data.items():
                setattr(account, field, value)
            await session.commit()
            # refresh is needed before closing the session: updated_at is computed
            # on the DB side (onupdate), and without it response serialization
            # raises DetachedInstanceError → «срабатывает только со второго раза»
            await session.refresh(account)
        await _invalidate_analytics()
        return account

    @classmethod
    async def set_archived(
        cls,
        account_id: int,
        user_id,
        is_archived: bool,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> AccountModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            account = await _get_owned_account(session, account_id, user_id)
            account.is_archived = is_archived
            await session.commit()
            await session.refresh(account)
        await _invalidate_analytics()
        return account

    @classmethod
    async def set_excluded(
        cls,
        account_id: int,
        user_id,
        is_excluded: bool,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> AccountModel:
        """The 'excluded from statistics' flag: the account stays, but does not affect totals."""
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            account = await _get_owned_account(session, account_id, user_id)
            account.is_excluded = is_excluded
            await session.commit()
            # refresh is needed before closing the session: updated_at is computed
            # on the DB side, and without it response serialization would try to
            # lazy-load the object outside the session
            await session.refresh(account)
        # An excluded account drops out of all totals and charts
        await _invalidate_analytics()
        return account

    @classmethod
    async def get_summary(
        cls,
        account_id: int,
        user_id,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> AccountSummary:
        """Account card: balance and turnover for the period in the base currency."""
        start_date, end_date = normalize_period(start_date, end_date)
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            account = await _get_owned_account(session, account_id, user_id)
            # We compute turnover for all accounts and pick the one we need: one
            # query is cheaper than a separate selection per account.
            rows = await TransactionDAO.totals_by_account(
                session,
                user_id,
                start_date=start_date,
                end_date=end_date,
                only_statistics=False,
            )
            row = next((item for item in rows if item.account_id == account_id), None)
            income = round(float(row.income), 2) if row else 0.0
            expense = round(float(row.expense), 2) if row else 0.0
            count = int(row.count) if row else 0

            # "Bank-style" balance: at end of period, not current.
            # Current balance minus everything that happened after end_date.
            later = 0.0
            incoming = 0.0
            if end_date is not None:
                deltas = await TransactionDAO.signed_totals_after_by_account(
                    session, user_id, end_date, account_ids=[account.id]
                )
                later = deltas.get(account.id, 0.0)
                transfers = await TransactionDAO.incoming_transfers_after_by_account(
                    session, user_id, end_date, account_ids=[account.id]
                )
                incoming = transfers.get(account.id, 0.0)

        return AccountSummary(
            account_id=account.id,
            name=account.name,
            currency_id=account.currency_id,
            balance=round(float(account.balance) - later - incoming, 2),
            is_archived=account.is_archived,
            is_excluded=account.is_excluded,
            income=income,
            expense=expense,
            net=round(income - expense, 2),
            transactions_count=count,
            start_date=start_date,
            end_date=end_date,
        )

    @classmethod
    async def delete_for_user(
        cls,
        account_id: int,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> None:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            account = await _get_owned_account(session, account_id, user_id)
            await cls.dao.delete(session, AccountModel.id == account.id)
            await session.commit()
        await _invalidate_analytics()

    @classmethod
    async def get_balance_overview(
        cls,
        user_id,
        end_date: Optional[datetime] = None,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> BalanceOverview:
        """Account balances in the base currency.

        ``end_date`` enables "bank statement" mode: the balance is taken at the
        end of the period (current balance minus everything that happened
        later), so when the user switches the period the widget shows that
        moment's figure instead of today's.
        """
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            # Accounts excluded from statistics do not participate in the overall balance
            accounts = await cls.dao.find_all_by_user(
                session,
                user_id,
                include_archived=False,
                include_excluded=False,
                limit=500,
            )
            later: dict = {}
            incoming: dict = {}
            if end_date is not None and accounts:
                account_ids = [account.id for account in accounts]
                later = await TransactionDAO.signed_totals_after_by_account(
                    session,
                    user_id,
                    end_date,
                    account_ids=account_ids,
                )
                incoming = await TransactionDAO.incoming_transfers_after_by_account(
                    session,
                    user_id,
                    end_date,
                    account_ids=account_ids,
                )

            # The grand total is computed in the user's base currency, not USD.
            # Personal rates override the catalog — otherwise the dashboard
            # total would diverge from the Currencies screen.
            base_rate = await _resolve_base_rate(session, user_id)
            overrides = {
                row.code: float(row.rate)
                for row in await UserCurrencyRateDAO.find_all_by_user(session, user_id)
                if row.rate and row.rate > 0
            }
            items: List[BalanceOverviewAccount] = []
            total = 0.0
            for account in accounts:
                balance = round(
                    float(account.balance) - later.get(account.id, 0.0) - incoming.get(account.id, 0.0),
                    2,
                )
                currency_rate = overrides.get(
                    (account.currency_id or "").upper(),
                    float(account.currency.exchange_rate_to_base),
                )
                balance_base = convert_amount(balance, currency_rate, base_rate)
                items.append(
                    BalanceOverviewAccount(
                        account_id=account.id,
                        name=account.name,
                        currency_id=account.currency_id,
                        balance=balance,
                        balance_base=balance_base,
                        is_archived=account.is_archived,
                        is_excluded=account.is_excluded,
                    )
                )
                total += balance_base
        return BalanceOverview(total=round(total, 2), accounts=items)


class CategoryService(BaseService[CategoryModel, CategoryCreate, CategoryUpdate]):
    dao = CategoryDAO

    @classmethod
    async def get_list_by_user(
        cls,
        user_id,
        category_type: Optional[CategoryType] = None,
        parent_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> List[CategoryModel]:
        from ..cache import Cache

        key = Cache.make_key(
            "categories:list",
            user=str(user_id),
            type=category_type.value if category_type is not None else None,
            parent=parent_id,
            offset=offset,
            limit=limit,
        )
        hit = await Cache.get(key)
        if hit is not None:
            from .schemas import Category

            return [Category(**item) for item in hit]

        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            categories = await cls.dao.find_all_by_user(
                session,
                user_id,
                category_type=category_type,
                parent_id=parent_id,
                offset=offset,
                limit=limit,
            )
        await Cache.set(key, [c.__dict__ for c in categories], ttl=3600)
        return categories

    @classmethod
    async def get_by_user(
        cls,
        category_id: int,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> CategoryModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            return await _get_owned_category(session, category_id, user_id)

    @classmethod
    async def create_for_user(
        cls,
        schema: CategoryCreate,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> CategoryModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            if schema.parent_id is not None:
                parent = await _get_owned_category(session, schema.parent_id, user_id)
                _validate_category_type(parent, TransactionType(schema.type.value))
            category = await cls.dao.create(session, {**schema.model_dump(), "user_id": user_id})
            if category is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Category creation conflict",
                )
            await session.commit()
        await _invalidate_categories()
        return category

    @classmethod
    async def create_defaults_for_user(
        cls, user_id, session_maker: Optional[async_sessionmaker] = None
    ) -> List[CategoryModel]:
        """Creates the standard set of categories and subcategories.

        Called once at registration: the user immediately gets a familiar
        structure and can rename, recolor or delete it — these are regular
        user categories. The whole set is written in one transaction: either
        all categories or none.
        """
        from .default_categories import default_categories

        maker = _resolve_session_maker(session_maker)
        created: List[CategoryModel] = []
        async with maker() as session:
            for spec, category_type in default_categories():
                name, icon, color, children = spec
                parent = await cls.dao.create(
                    session,
                    {
                        "name": name,
                        "type": CategoryType(category_type),
                        "parent_id": None,
                        "icon": icon,
                        "color": color,
                        "user_id": user_id,
                    },
                )
                if parent is None:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Default category creation conflict",
                    )
                created.append(parent)
                for child_name, child_icon, child_color in children:
                    child = await cls.dao.create(
                        session,
                        {
                            "name": child_name,
                            "type": CategoryType(category_type),
                            "parent_id": parent.id,
                            "icon": child_icon,
                            "color": child_color,
                            "user_id": user_id,
                        },
                    )
                    if child is None:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Default subcategory creation conflict",
                        )
                    created.append(child)
            await session.commit()
        await _invalidate_categories()
        return created

    @classmethod
    async def update_for_user(
        cls,
        category_id: int,
        schema: CategoryUpdate,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> CategoryModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            category = await _get_owned_category(session, category_id, user_id)
            update_data = schema.model_dump(exclude_unset=True)
            parent_id = update_data.get("parent_id")
            if parent_id is not None:
                if parent_id == category.id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Category cannot be its own parent",
                    )
                parent = await _get_owned_category(session, parent_id, user_id)
                category_type = update_data.get("type", category.type)
                _validate_category_type(parent, TransactionType(category_type.value))
            for field, value in update_data.items():
                setattr(category, field, value)
            await session.commit()
            # same as accounts: updated_at is server-side onupdate
            await session.refresh(category)
        await _invalidate_categories()
        return category

    @classmethod
    async def delete_for_user(
        cls,
        category_id: int,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> None:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            category = await _get_owned_category(session, category_id, user_id)
            children_count = await cls.dao.count_children(session, category.id)
            if children_count:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Category has subcategories",
                )
            transactions_count = await TransactionDAO.count_by_category(session, category.id)
            if transactions_count:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Category is used by transactions",
                )
            await cls.dao.delete(session, CategoryModel.id == category.id)
            await session.commit()
        await _invalidate_categories()

    @classmethod
    async def get_tree(
        cls,
        user_id,
        category_type: Optional[CategoryType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> List[CategoryNode]:
        """Category tree with subcategories and transaction counts.

        Settings and the transaction dialog show a category together with its
        subcategories, so the tree is assembled in one response: without it the
        UI would make N+1 requests per category.
        """
        from ..cache import Cache

        start_date, end_date = normalize_period(start_date, end_date)
        key = Cache.make_key(
            "categories:tree",
            user=str(user_id),
            type=category_type.value if category_type is not None else None,
            start=start_date,
            end=end_date,
        )
        hit = await Cache.get(key)
        if hit is not None:
            return [CategoryNode(**item) for item in hit]

        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            categories = await cls.dao.find_all_by_user(session, user_id, category_type=category_type, limit=500)
            rows = await TransactionDAO.totals_by_category(
                session,
                user_id,
                start_date=start_date,
                end_date=end_date,
                only_statistics=True,
            )
        counts = {row.group_id: (int(row.count), round(float(row.total), 2)) for row in rows}

        nodes = {
            category.id: CategoryNode(
                id=category.id,
                name=category.name,
                type=category.type,
                parent_id=category.parent_id,
                icon=category.icon,
                color=category.color,
                transactions_count=counts.get(category.id, (0, 0.0))[0],
            )
            for category in categories
        }
        roots: List[CategoryNode] = []
        for category in categories:
            node = nodes[category.id]
            parent = nodes.get(category.parent_id) if category.parent_id else None
            if parent is not None:
                parent.children.append(node)
            else:
                roots.append(node)
        await Cache.set(key, [n.model_dump() for n in roots], ttl=3600)
        return roots

    @classmethod
    async def get_stats(
        cls,
        user_id,
        category_type: Optional[CategoryType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> List[CategoryStat]:
        """How many records and what total amount each category has."""
        start_date, end_date = normalize_period(start_date, end_date)
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            rows = await TransactionDAO.totals_by_category(
                session,
                user_id,
                start_date=start_date,
                end_date=end_date,
                category_type=category_type,
            )
        return [
            CategoryStat(
                category_id=row.group_id,
                name=row.name,
                type=row.category_type,
                parent_id=row.parent_id,
                icon=row.icon,
                color=row.color,
                transactions_count=int(row.count),
                total=round(float(row.total), 2),
            )
            for row in rows
        ]


class TransactionService(BaseService[TransactionModel, TransactionCreate, TransactionUpdate]):
    dao = TransactionDAO

    @classmethod
    def _normalized_filters(cls, start_date, end_date, filters: dict) -> dict:
        """Normalizes period boundaries and drops empty values.

        The Transactions screen sends empty strings and empty lists when a filter
        is unset: they must be ignored, not filtered "by emptiness".
        """
        start_date, end_date = normalize_period(start_date, end_date)
        cleaned = {key: value for key, value in filters.items() if value not in (None, "", [], ())}
        return {"start_date": start_date, "end_date": end_date, **cleaned}

    @classmethod
    async def get_list_by_user(
        cls,
        user_id,
        account_id: Optional[int] = None,
        category_id: Optional[int] = None,
        transaction_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        offset: int = 0,
        limit: int = 100,
        sort: str = "date_desc",
        session_maker: Optional[async_sessionmaker] = None,
        **filters,
    ) -> List[TransactionModel]:
        params = cls._normalized_filters(start_date, end_date, filters)
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            return await cls.dao.find_filtered(
                session,
                user_id,
                account_id=account_id,
                category_id=category_id,
                transaction_type=transaction_type,
                offset=offset,
                limit=limit,
                sort=sort,
                **params,
            )

    @classmethod
    async def count_by_user(
        cls,
        user_id,
        account_id: Optional[int] = None,
        category_id: Optional[int] = None,
        transaction_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: Optional[async_sessionmaker] = None,
        **filters,
    ) -> int:
        params = cls._normalized_filters(start_date, end_date, filters)
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            return await cls.dao.count_filtered(
                session,
                user_id,
                account_id=account_id,
                category_id=category_id,
                transaction_type=transaction_type,
                **params,
            )

    @classmethod
    async def bulk_delete(cls, ids: List[int], user_id, session_maker: Optional[async_sessionmaker] = None) -> tuple:
        """Deletes the selected records and rolls back their effect on balances.

        Returns ``(how many deleted, which ids were not found)``. Other users'
        records are not touched: they end up in "missing".
        """
        maker = _resolve_session_maker(session_maker)
        deleted = 0
        missing: List[int] = []
        async with maker() as session:
            transactions = await TransactionDAO.find_many_by_user(session, user_id, ids)
            found = {transaction.id: transaction for transaction in transactions}
            missing = [identifier for identifier in ids if identifier not in found]

            for transaction in transactions:
                account = transaction.account
                transaction_rate = await _effective_currency_rate(session, user_id, transaction.currency_id)
                account_rate = await _effective_currency_rate(session, user_id, account.currency_id)
                account.balance = round(
                    account.balance
                    - _converted_delta(
                        transaction.type,
                        transaction.amount,
                        transaction_rate,
                        account_rate,
                    ),
                    2,
                )
                if transaction.type == TransactionType.TRANSFER and transaction.transfer_account is not None:
                    transaction.transfer_account.balance = round(
                        transaction.transfer_account.balance
                        - convert_amount(
                            transaction.amount,
                            transaction_rate,
                            await _effective_currency_rate(
                                session,
                                user_id,
                                transaction.transfer_account.currency_id,
                            ),
                        ),
                        2,
                    )
                await cls.dao.delete(session, TransactionModel.id == transaction.id)
                deleted += 1
            await session.commit()
        await _invalidate_analytics()
        return deleted, missing

    @classmethod
    async def get_by_user(
        cls,
        transaction_id: int,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> TransactionModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            transaction = await cls.dao.find_one_by_user(session, transaction_id, user_id)
        if transaction is None:
            raise _not_found("Transaction not found")
        return transaction

    @classmethod
    async def create_for_user(
        cls,
        schema: TransactionCreate,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> TransactionModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            account = await _get_owned_account(session, schema.account_id, user_id)
            _ensure_not_crypto(account)
            transfer_account = None
            if schema.type == TransactionType.TRANSFER:
                transfer_account = await _resolve_transfer_account(
                    session,
                    user_id,
                    schema.account_id,
                    schema.transfer_account_id,
                    schema.currency_id,
                    session_maker=maker,
                )
                _ensure_not_crypto(transfer_account)
                category = await _transfer_category(session, user_id)
            else:
                if schema.category_id is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Category is required",
                    )
                category = await _get_owned_category(session, schema.category_id, user_id)
                _validate_category_type(category, schema.type)
            currency = await _get_currency(session, schema.currency_id)

            tag_ids = schema.tag_ids
            await ensure_tags_owned(session, tag_ids, user_id)

            # tag_ids is not a table column, so everything else goes into the
            # insert. The transfer category is set by the server, not the client.
            payload = schema.model_dump(exclude={"tag_ids"})
            payload["category_id"] = category.id
            if transfer_account is None:
                payload["transfer_account_id"] = None
            transaction = await cls.dao.create(session, payload)
            if transaction is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Transaction creation conflict",
                )

            if tag_ids:
                await attach_tags(session, transaction.id, tag_ids)

            transaction_rate = await _effective_currency_rate(session, user_id, currency.code)
            account.balance = round(
                account.balance
                + _converted_delta(
                    schema.type,
                    schema.amount,
                    transaction_rate,
                    await _effective_currency_rate(session, user_id, account.currency_id),
                ),
                2,
            )
            if transfer_account is not None:
                transfer_account.balance = round(
                    transfer_account.balance
                    + convert_amount(
                        schema.amount,
                        transaction_rate,
                        await _effective_currency_rate(session, user_id, transfer_account.currency_id),
                    ),
                    2,
                )
            await session.commit()
            created = await cls.dao.find_one_by_user(session, transaction.id, user_id)
        await _invalidate_analytics()
        return created or transaction

    @classmethod
    async def update_for_user(
        cls,
        transaction_id: int,
        schema: TransactionUpdate,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> TransactionModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            transaction = await cls.dao.find_one_by_user(session, transaction_id, user_id)
            if transaction is None:
                raise _not_found("Transaction not found")

            update_data = schema.model_dump(exclude_unset=True)
            tag_ids = update_data.pop("tag_ids", None)
            if tag_ids is not None:
                await ensure_tags_owned(session, tag_ids, user_id)
                await attach_tags(session, transaction.id, tag_ids)

            old_account = transaction.account
            old_currency = await _get_currency(session, transaction.currency_id)
            old_currency_rate = await _effective_currency_rate(session, user_id, old_currency.code)
            old_delta = _converted_delta(
                transaction.type,
                transaction.amount,
                old_currency_rate,
                await _effective_currency_rate(session, user_id, old_account.currency_id),
            )

            # The old transfer already credited the destination account: on any
            # change we first roll back that credit.
            old_transfer_account = (
                transaction.transfer_account if transaction.type == TransactionType.TRANSFER else None
            )
            old_transfer_credit = 0.0
            if old_transfer_account is not None:
                old_transfer_credit = convert_amount(
                    transaction.amount,
                    old_currency_rate,
                    await _effective_currency_rate(session, user_id, old_transfer_account.currency_id),
                )

            account = old_account
            if "account_id" in update_data:
                account = await _get_owned_account(session, update_data["account_id"], user_id)
                _ensure_not_crypto(account)

            category = transaction.category
            if "category_id" in update_data:
                category = await _get_owned_category(session, update_data["category_id"], user_id)

            new_type = update_data.get("type", transaction.type)
            new_amount = update_data.get("amount", transaction.amount)
            new_currency = await _get_currency(session, update_data.get("currency_id", transaction.currency_id))
            if new_type == TransactionType.TRANSFER:
                if category.type != CategoryType.TRANSFER:
                    category = await _transfer_category(session, user_id)
                update_data["category_id"] = category.id
                transfer_account = await _resolve_transfer_account(
                    session,
                    user_id,
                    account.id,
                    update_data.get("transfer_account_id", transaction.transfer_account_id),
                    new_currency.code,
                    session_maker=maker,
                )
                _ensure_not_crypto(transfer_account)
                update_data["transfer_account_id"] = transfer_account.id
            else:
                _validate_category_type(category, new_type)
                transfer_account = None
                update_data["transfer_account_id"] = None
            new_currency_rate = await _effective_currency_rate(session, user_id, new_currency.code)
            new_delta = _converted_delta(
                new_type,
                new_amount,
                new_currency_rate,
                await _effective_currency_rate(session, user_id, account.currency_id),
            )

            if old_transfer_account is not None:
                old_transfer_account.balance = round(old_transfer_account.balance - old_transfer_credit, 2)
            old_account.balance = round(old_account.balance - old_delta, 2)
            account.balance = round(account.balance + new_delta, 2)
            if transfer_account is not None:
                transfer_account.balance = round(
                    transfer_account.balance
                    + convert_amount(
                        new_amount,
                        new_currency_rate,
                        await _effective_currency_rate(session, user_id, transfer_account.currency_id),
                    ),
                    2,
                )

            for field, value in update_data.items():
                setattr(transaction, field, value)

            await session.commit()
            updated = await cls.dao.find_one_by_user(session, transaction.id, user_id)
        await _invalidate_analytics()
        return updated or transaction

    @classmethod
    async def delete_for_user(
        cls,
        transaction_id: int,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> None:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            transaction = await cls.dao.find_one_by_user(session, transaction_id, user_id)
            if transaction is None:
                raise _not_found("Transaction not found")

            account = transaction.account
            currency = await _get_currency(session, transaction.currency_id)
            currency_rate = await _effective_currency_rate(session, user_id, currency.code)
            account.balance = round(
                account.balance
                - _converted_delta(
                    transaction.type,
                    transaction.amount,
                    currency_rate,
                    await _effective_currency_rate(session, user_id, account.currency_id),
                ),
                2,
            )
            if transaction.type == TransactionType.TRANSFER and transaction.transfer_account is not None:
                transaction.transfer_account.balance = round(
                    transaction.transfer_account.balance
                    - convert_amount(
                        transaction.amount,
                        currency_rate,
                        await _effective_currency_rate(session, user_id, transaction.transfer_account.currency_id),
                    ),
                    2,
                )
            await cls.dao.delete(session, TransactionModel.id == transaction.id)
            await session.commit()
        await _invalidate_analytics()

    @classmethod
    async def get_summary(
        cls,
        user_id,
        transaction_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> TransactionSummary:
        start_date, end_date = normalize_period(start_date, end_date)
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            rows = await cls.dao.sum_by_category(
                session,
                user_id,
                transaction_type=transaction_type,
                start_date=start_date,
                end_date=end_date,
            )
            total = await cls.dao.sum_filtered(
                session,
                user_id,
                transaction_type=transaction_type,
                start_date=start_date,
                end_date=end_date,
            )
            transactions_count = await cls.dao.count_filtered(
                session,
                user_id,
                transaction_type=transaction_type,
                start_date=start_date,
                end_date=end_date,
            )

        by_category = [
            CategoryTotal(
                category_id=row.category_id,
                name=row.name,
                color=row.color,
                icon=row.icon,
                total=round(float(row.total), 2),
                transactions_count=int(row.transactions_count),
            )
            for row in rows
        ]
        return TransactionSummary(
            total=round(total, 2),
            transactions_count=transactions_count,
            by_category=by_category,
            start_date=start_date,
            end_date=end_date,
        )

    # ------------------------------------------------------------------ #
    #  Import of records from an exported file
    # ------------------------------------------------------------------ #

    IMPORT_LIMIT = 5000
    IMPORT_HEADER = ["date", "type", "account", "category", "amount", "currency", "note"]

    @classmethod
    def _parse_import_rows(cls, payload: TransactionImportRequest) -> List[dict]:
        """Rows as dicts from an exported CSV (the export header) or JSON."""
        if payload.format == "json":
            try:
                data = json.loads(payload.content)
            except json.JSONDecodeError as error:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid JSON: {error}")
            if not isinstance(data, list):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="JSON must be an array of exported records",
                )
            return [
                {
                    "date": item.get("date"),
                    "type": item.get("type"),
                    "account": item.get("account_name"),
                    "category": item.get("category_name"),
                    "amount": item.get("amount"),
                    "currency": item.get("currency_id"),
                    "note": item.get("note"),
                }
                for item in data
                if isinstance(item, dict)
            ]
        reader = csv.DictReader(io.StringIO(payload.content))
        header = {(name or "").strip().lower() for name in (reader.fieldnames or [])}
        if not {"date", "type", "account", "amount"}.issubset(header):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV header must match the export: " + ",".join(cls.IMPORT_HEADER),
            )
        return [
            {(k or "").strip().lower(): (v.strip() if isinstance(v, str) else v) for k, v in raw.items() if k}
            for raw in reader
        ]

    @staticmethod
    def _parse_import_date(value: object) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        text = str(value or "").strip()
        if not text:
            return None
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                pass
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    @staticmethod
    def _skip_import_row(result: TransactionImportResult, message: str) -> None:
        result.skipped += 1
        if len(result.errors) < 20:
            result.errors.append(message)

    @classmethod
    async def _import_row(
        cls,
        row: dict,
        number: int,
        user_id,
        accounts: dict,
        categories: dict,
        result: TransactionImportResult,
        session_maker: Optional[async_sessionmaker],
    ) -> None:
        raw_type = str(row.get("type") or "").strip().lower()
        account_name = str(row.get("account") or "").strip()
        category_name = str(row.get("category") or "").strip()
        currency = str(row.get("currency") or "").strip().upper()
        date = cls._parse_import_date(row.get("date"))
        try:
            amount = float(str(row.get("amount") or "").replace(",", "."))
        except ValueError:
            amount = None

        if raw_type == "transfer":
            cls._skip_import_row(
                result, f"Row {number}: transfers are not imported (the export lacks the destination account)"
            )
            return
        if raw_type not in ("income", "expense"):
            cls._skip_import_row(result, f"Row {number}: type must be income, expense or transfer")
            return
        if not account_name:
            cls._skip_import_row(result, f"Row {number}: account name is required")
            return
        if not category_name:
            cls._skip_import_row(result, f"Row {number}: category name is required")
            return
        if len(currency) != 3:
            cls._skip_import_row(result, f"Row {number}: currency must be a 3-letter code")
            return
        if amount is None or amount <= 0:
            cls._skip_import_row(result, f"Row {number}: amount must be a positive number")
            return
        if date is None:
            cls._skip_import_row(result, f"Row {number}: unrecognized date, expected YYYY-MM-DD HH:MM")
            return

        try:
            account_id = accounts.get(account_name)
            if account_id is None:
                account = await AccountService.create_for_user(
                    schema=AccountCreate(
                        name=account_name,
                        type=AccountType.CHECKING,
                        currency_id=currency,
                        balance=0.0,
                    ),
                    user_id=user_id,
                    session_maker=session_maker,
                )
                account_id = account.id
                accounts[account_name] = account_id
                result.accounts_created += 1
            category_id = categories.get((category_name, raw_type))
            if category_id is None:
                category = await CategoryService.create_for_user(
                    schema=CategoryCreate(name=category_name, type=CategoryType(raw_type)),
                    user_id=user_id,
                    session_maker=session_maker,
                )
                category_id = category.id
                categories[(category_name, raw_type)] = category_id
                result.categories_created += 1
            await cls.create_for_user(
                schema=TransactionCreate(
                    account_id=account_id,
                    category_id=category_id,
                    amount=amount,
                    currency_id=currency,
                    type=TransactionType(raw_type),
                    date=date,
                    note=(str(row.get("note") or "").strip() or None),
                ),
                user_id=user_id,
                session_maker=session_maker,
            )
            result.created += 1
        except HTTPException as error:
            cls._skip_import_row(result, f"Row {number}: {error.detail}")

    @classmethod
    async def import_from_text(
        cls,
        payload: TransactionImportRequest,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> TransactionImportResult:
        """Import records from an exported file (CSV or JSON of the export endpoint).

        Accounts and categories are matched by name; missing ones are created
        for the user: a checking account in the record currency and a category
        of the record type. Bad rows are skipped with a reason, not aborted.
        """
        rows = cls._parse_import_rows(payload)
        result = TransactionImportResult()
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            accounts = {
                account.name: account.id
                for account in await AccountDAO.find_all_by_user(session, user_id, include_archived=True, limit=500)
            }
            categories = {
                (category.name, category.type.value): category.id
                for category in await CategoryDAO.find_all_by_user(session, user_id, limit=1000)
            }
        if len(rows) > cls.IMPORT_LIMIT:
            cls._skip_import_row(result, f"Only the first {cls.IMPORT_LIMIT} rows are imported")
            result.skipped += len(rows) - cls.IMPORT_LIMIT
        for number, row in enumerate(rows[: cls.IMPORT_LIMIT], start=1):
            await cls._import_row(row, number, user_id, accounts, categories, result, maker)
        if result.created:
            await _invalidate_analytics()
        return result


class SubscriptionService(BaseService[SubscriptionModel, SubscriptionCreate, SubscriptionUpdate]):
    dao = SubscriptionDAO

    @classmethod
    async def get_list_by_user(
        cls,
        user_id,
        is_active: Optional[bool] = None,
        offset: int = 0,
        limit: int = 100,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> List[SubscriptionModel]:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            return await cls.dao.find_all_by_user(session, user_id, is_active=is_active, offset=offset, limit=limit)

    @classmethod
    async def get_by_user(
        cls,
        subscription_id: int,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> SubscriptionModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            subscription = await cls.dao.find_one_by_user(session, subscription_id, user_id)
        if subscription is None:
            raise _not_found("Subscription not found")
        return subscription

    @classmethod
    async def get_upcoming(
        cls,
        user_id,
        days: int = 7,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> List[SubscriptionModel]:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            return await cls.dao.find_upcoming(session, user_id, before=datetime.now() + timedelta(days=days))

    @classmethod
    async def create_for_user(
        cls,
        schema: SubscriptionCreate,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> SubscriptionModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            transaction = await TransactionDAO.find_one_by_user(session, schema.transaction_id, user_id)
            if transaction is None:
                raise _not_found("Transaction not found")
            if transaction.type == TransactionType.INCOME:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Income transactions cannot be subscriptions",
                )
            if schema.next_payment_date < transaction.date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="next_payment_date must not be earlier than the transaction date",
                )
            existing = await TransactionDAO.find_related_subscription(session, transaction.id)
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Transaction already has a subscription",
                )

            subscription = await cls.dao.create(session, schema)
            if subscription is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Subscription creation conflict",
                )
            transaction.is_subscription = True
            await session.commit()
            created = await cls.dao.find_one_by_user(session, subscription.id, user_id)
        return created or subscription

    @classmethod
    async def update_for_user(
        cls,
        subscription_id: int,
        schema: SubscriptionUpdate,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> SubscriptionModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            subscription = await cls.dao.find_one_by_user(session, subscription_id, user_id)
            if subscription is None:
                raise _not_found("Subscription not found")

            for field, value in schema.model_dump(exclude_unset=True).items():
                setattr(subscription, field, value)

            if "is_active" in schema.model_dump(exclude_unset=True):
                subscription.transaction.is_subscription = subscription.is_active

            await session.commit()
            updated = await cls.dao.find_one_by_user(session, subscription.id, user_id)
        return updated or subscription

    @classmethod
    async def advance_next_payment(
        cls,
        subscription_id: int,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> SubscriptionModel:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            subscription = await cls.dao.find_one_by_user(session, subscription_id, user_id)
            if subscription is None:
                raise _not_found("Subscription not found")
            subscription.next_payment_date = calculate_next_payment_date(
                subscription.frequency, subscription.next_payment_date
            )
            await session.commit()
            updated = await cls.dao.find_one_by_user(session, subscription.id, user_id)
        return updated or subscription

    @classmethod
    async def delete_for_user(
        cls,
        subscription_id: int,
        user_id,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> None:
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            subscription = await cls.dao.find_one_by_user(session, subscription_id, user_id)
            if subscription is None:
                raise _not_found("Subscription not found")
            subscription.transaction.is_subscription = False
            await cls.dao.delete(session, SubscriptionModel.id == subscription.id)
            await session.commit()
