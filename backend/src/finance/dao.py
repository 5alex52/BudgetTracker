from collections.abc import Sequence
from datetime import datetime
from typing import List
from typing import Optional

from sqlalchemy import case
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy import Select
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.orm import selectinload

from ..dao import BaseDAO
from ..users.models import UserModel
from .models import AccountModel
from .models import CategoryModel
from .models import CurrencyModel
from .models import SubscriptionModel
from .models import transaction_tags
from .models import TransactionModel
from .models import UserCurrencyRateModel
from .schemas import AccountCreate
from .schemas import AccountUpdate
from .schemas import CategoryCreate
from .schemas import CategoryType
from .schemas import CategoryUpdate
from .schemas import CurrencyCreate
from .schemas import CurrencyUpdate
from .schemas import SubscriptionCreate
from .schemas import SubscriptionUpdate
from .schemas import TransactionCreate
from .schemas import TransactionType
from .schemas import TransactionUpdate


class CurrencyDAO(BaseDAO[CurrencyModel, CurrencyCreate, CurrencyUpdate]):
    model = CurrencyModel

    @classmethod
    async def find_all_ordered(
        cls, session: AsyncSession, offset: int = 0, limit: int = 100
    ) -> List[CurrencyModel]:
        stmt = select(cls.model).order_by(cls.model.code).offset(offset).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())


class AccountDAO(BaseDAO[AccountModel, AccountCreate, AccountUpdate]):
    model = AccountModel

    @classmethod
    async def find_all_by_user(
        cls,
        session: AsyncSession,
        user_id,
        include_archived: bool = False,
        include_excluded: bool = True,
        offset: int = 0,
        limit: int = 100,
    ) -> List[AccountModel]:
        stmt = select(cls.model).where(cls.model.user_id == user_id)
        if not include_archived:
            stmt = stmt.where(cls.model.is_archived.is_(False))
        if not include_excluded:
            stmt = stmt.where(cls.model.is_excluded.is_(False))
        stmt = stmt.order_by(cls.model.id).offset(offset).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    def statistics_stmt(cls, user_id) -> Select:
        """Accounts that participate in statistics: active and not excluded."""
        return select(cls.model).where(
            cls.model.user_id == user_id,
            cls.model.is_archived.is_(False),
            cls.model.is_excluded.is_(False),
        )

    @classmethod
    async def find_one_by_user(
        cls, session: AsyncSession, account_id: int, user_id
    ) -> Optional[AccountModel]:
        stmt = select(cls.model).where(
            cls.model.id == account_id, cls.model.user_id == user_id
        )
        result = await session.execute(stmt)
        return result.scalars().one_or_none()

    @classmethod
    async def count_by_user(
        cls, session: AsyncSession, user_id, include_archived: bool = False
    ) -> int:
        """How many non-archived accounts the user has."""
        stmt = select(func.count(cls.model.id)).where(cls.model.user_id == user_id)
        if not include_archived:
            stmt = stmt.where(cls.model.is_archived.is_(False))
        result = await session.execute(stmt)
        return int(result.scalar() or 0)


class CategoryDAO(BaseDAO[CategoryModel, CategoryCreate, CategoryUpdate]):
    model = CategoryModel

    @classmethod
    async def find_all_by_user(
        cls,
        session: AsyncSession,
        user_id,
        category_type: Optional[CategoryType] = None,
        parent_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[CategoryModel]:
        stmt = select(cls.model).where(cls.model.user_id == user_id)
        if category_type is not None:
            stmt = stmt.where(cls.model.type == category_type)
        if parent_id is not None:
            stmt = stmt.where(cls.model.parent_id == parent_id)
        stmt = stmt.order_by(cls.model.name).offset(offset).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def with_descendants(
        cls, session: AsyncSession, user_id, category_ids: Sequence[int]
    ) -> List[int]:
        """Selected categories together with all nested ones.

        The "Food" filter must show "Groceries" and "Cafes" too: the user picks
        a branch, not a single row. Nesting is expanded in a loop because the
        tree cannot be hardcoded to two levels.
        """
        known = {int(identifier) for identifier in category_ids}
        frontier = set(known)
        while frontier:
            stmt = select(cls.model.id).where(
                cls.model.user_id == user_id, cls.model.parent_id.in_(list(frontier))
            )
            result = await session.execute(stmt)
            frontier = set(result.scalars().all()) - known
            known |= frontier
        return sorted(known)

    @classmethod
    async def find_one_by_user(
        cls, session: AsyncSession, category_id: int, user_id
    ) -> Optional[CategoryModel]:
        stmt = select(cls.model).where(
            cls.model.id == category_id, cls.model.user_id == user_id
        )
        result = await session.execute(stmt)
        return result.scalars().one_or_none()

    @classmethod
    async def count_children(cls, session: AsyncSession, category_id: int) -> int:
        stmt = select(func.count(cls.model.id)).where(
            cls.model.parent_id == category_id
        )
        result = await session.execute(stmt)
        return int(result.scalar() or 0)


class TransactionDAO(BaseDAO[TransactionModel, TransactionCreate, TransactionUpdate]):
    model = TransactionModel

    @classmethod
    async def signed_totals_after_by_account(
        cls,
        session: AsyncSession,
        user_id,
        moment: datetime,
        account_ids: Optional[Sequence[int]] = None,
    ) -> dict:
        """Signed turnover after a moment, per account and in the account currency.

        It is used to build the "bank-style" balance at a date: current balance
        minus everything that happened after the chosen date. The amount is
        converted to the account currency using the same rate ratio as when a
        transaction changes the balance.
        """
        account_currency = aliased(CurrencyModel)
        signed = case(
            (TransactionModel.type == TransactionType.INCOME, TransactionModel.amount),
            else_=-TransactionModel.amount,
        )
        tx_override = (
            select(UserCurrencyRateModel.rate)
            .where(
                UserCurrencyRateModel.user_id == user_id,
                UserCurrencyRateModel.code == TransactionModel.currency_id,
            )
            .scalar_subquery()
        )
        account_override = (
            select(UserCurrencyRateModel.rate)
            .where(
                UserCurrencyRateModel.user_id == user_id,
                UserCurrencyRateModel.code == AccountModel.currency_id,
            )
            .scalar_subquery()
        )
        tx_rate = func.coalesce(tx_override, CurrencyModel.exchange_rate_to_base)
        account_rate = func.coalesce(
            account_override, account_currency.exchange_rate_to_base
        )
        rate_ratio = tx_rate / func.nullif(account_rate, 0.0)
        stmt = (
            select(
                TransactionModel.account_id,
                func.coalesce(func.sum(signed * rate_ratio), 0.0).label("total"),
            )
            .select_from(TransactionModel)
            .join(AccountModel, TransactionModel.account_id == AccountModel.id)
            .join(CurrencyModel, TransactionModel.currency_id == CurrencyModel.code)
            .join(account_currency, AccountModel.currency_id == account_currency.code)
            .where(AccountModel.user_id == user_id, TransactionModel.date > moment)
        )
        if account_ids is not None:
            stmt = stmt.where(TransactionModel.account_id.in_(list(account_ids)))
        stmt = stmt.group_by(TransactionModel.account_id)
        result = await session.execute(stmt)
        return {row.account_id: round(float(row.total), 2) for row in result.all()}

    @classmethod
    async def incoming_transfers_after_by_account(
        cls,
        session: AsyncSession,
        user_id,
        moment: datetime,
        account_ids: Optional[Sequence[int]] = None,
    ) -> dict:
        """How many transfers arrived at each account after the moment (in the account currency).

        A transfer is stored as one record on the source account, so the credit
        on the destination is not visible in ``signed_totals_after_by_account``.
        Without this query the historical balance of the destination account
        would be overstated.
        """
        dest_account = aliased(AccountModel)
        dest_currency = aliased(CurrencyModel)
        tx_override = (
            select(UserCurrencyRateModel.rate)
            .where(
                UserCurrencyRateModel.user_id == user_id,
                UserCurrencyRateModel.code == TransactionModel.currency_id,
            )
            .scalar_subquery()
        )
        dest_override = (
            select(UserCurrencyRateModel.rate)
            .where(
                UserCurrencyRateModel.user_id == user_id,
                UserCurrencyRateModel.code == dest_account.currency_id,
            )
            .scalar_subquery()
        )
        tx_rate = func.coalesce(tx_override, CurrencyModel.exchange_rate_to_base)
        dest_rate = func.coalesce(dest_override, dest_currency.exchange_rate_to_base)
        stmt = (
            select(
                TransactionModel.transfer_account_id,
                func.coalesce(
                    func.sum(
                        TransactionModel.amount * tx_rate / func.nullif(dest_rate, 0.0)
                    ),
                    0.0,
                ).label("total"),
            )
            .select_from(TransactionModel)
            .join(AccountModel, TransactionModel.account_id == AccountModel.id)
            .join(CurrencyModel, TransactionModel.currency_id == CurrencyModel.code)
            .join(dest_account, TransactionModel.transfer_account_id == dest_account.id)
            .join(dest_currency, dest_account.currency_id == dest_currency.code)
            .where(
                AccountModel.user_id == user_id,
                dest_account.user_id == user_id,
                TransactionModel.type == TransactionType.TRANSFER,
                TransactionModel.date > moment,
            )
        )
        if account_ids is not None:
            stmt = stmt.where(
                TransactionModel.transfer_account_id.in_(list(account_ids))
            )
        stmt = stmt.group_by(TransactionModel.transfer_account_id)
        result = await session.execute(stmt)
        return {
            row.transfer_account_id: round(float(row.total), 2) for row in result.all()
        }

    @classmethod
    def _filtered_stmt(
        cls,
        user_id,
        account_id: Optional[int] = None,
        category_id: Optional[int] = None,
        transaction_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        account_ids: Optional[Sequence[int]] = None,
        category_ids: Optional[Sequence[int]] = None,
        currency_ids: Optional[Sequence[str]] = None,
        transaction_types: Optional[Sequence[TransactionType]] = None,
        query: Optional[str] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        tag_ids: Optional[Sequence[int]] = None,
        only_statistics: bool = False,
    ) -> Select:
        """Base filter set for the transaction list and all aggregates.

        Single (``account_id``) and multiple (``account_ids``) filters are
        supported at the same time: the single ones are kept for backwards
        compatibility with already-published endpoints.

        ``only_statistics`` drops accounts flagged "excluded from statistics":
        aggregates then do not mix in money the user asked to ignore.
        """
        stmt = (
            select(cls.model)
            .join(AccountModel, cls.model.account_id == AccountModel.id)
            .where(AccountModel.user_id == user_id)
            .options(
                selectinload(cls.model.account),
                selectinload(cls.model.transfer_account),
                selectinload(cls.model.tags),
            )
        )
        if only_statistics:
            stmt = stmt.where(AccountModel.is_excluded.is_(False))
        if account_id is not None:
            stmt = stmt.where(cls.model.account_id == account_id)
        if account_ids:
            stmt = stmt.where(cls.model.account_id.in_(list(account_ids)))
        if category_id is not None:
            stmt = stmt.where(cls.model.category_id == category_id)
        if category_ids:
            stmt = stmt.where(cls.model.category_id.in_(list(category_ids)))
        if currency_ids:
            stmt = stmt.where(cls.model.currency_id.in_(list(currency_ids)))
        if transaction_type is not None:
            stmt = stmt.where(cls.model.type == transaction_type)
        if transaction_types:
            stmt = stmt.where(cls.model.type.in_(list(transaction_types)))
        if start_date is not None:
            stmt = stmt.where(cls.model.date >= start_date)
        if end_date is not None:
            stmt = stmt.where(cls.model.date <= end_date)
        if amount_min is not None:
            stmt = stmt.where(cls.model.amount >= amount_min)
        if amount_max is not None:
            stmt = stmt.where(cls.model.amount <= amount_max)
        if tag_ids:
            # "Records with at least one of the selected tags" — that is how the filter chips work
            stmt = stmt.where(
                cls.model.id.in_(
                    select(transaction_tags.c.transaction_id).where(
                        transaction_tags.c.tag_id.in_(list(tag_ids))
                    )
                )
            )
        if query:
            needle = f"%{query.strip().lower()}%"
            stmt = stmt.outerjoin(
                CategoryModel, cls.model.category_id == CategoryModel.id
            ).where(
                or_(
                    func.lower(func.coalesce(cls.model.note, "")).like(needle),
                    func.lower(CategoryModel.name).like(needle),
                    func.lower(AccountModel.name).like(needle),
                )
            )
        return stmt

    #: Supported sort modes for the transaction list
    SORT_OPTIONS = {
        "date_desc": ("date", True),
        "date_asc": ("date", False),
        "amount_desc": ("amount", True),
        "amount_asc": ("amount", False),
    }

    @classmethod
    async def _expand_categories(
        cls, session: AsyncSession, user_id, filters: dict
    ) -> dict:
        """Replaces selected categories with the list including nested ones.

        Without this, the "Food" filter would not find "Groceries": the record
        holds the subcategory id, but the user picked the parent.
        """
        ids = [int(identifier) for identifier in (filters.get("category_ids") or [])]
        single = filters.get("category_id")
        if single is not None:
            ids.append(int(single))
        if not ids:
            return filters
        expanded = await CategoryDAO.with_descendants(session, user_id, ids)
        updated = dict(filters)
        updated["category_id"] = None
        updated["category_ids"] = expanded
        return updated

    @classmethod
    async def find_filtered(
        cls,
        session: AsyncSession,
        user_id,
        account_id: Optional[int] = None,
        category_id: Optional[int] = None,
        transaction_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        offset: int = 0,
        limit: int = 100,
        sort: str = "date_desc",
        **filters,
    ) -> List[TransactionModel]:
        merged = dict(filters)
        if category_id is not None:
            merged["category_id"] = category_id
        merged = await cls._expand_categories(session, user_id, merged)

        stmt = cls._filtered_stmt(
            user_id=user_id,
            account_id=account_id,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date,
            **merged,
        )
        field, descending = cls.SORT_OPTIONS.get(sort, cls.SORT_OPTIONS["date_desc"])
        column = cls.model.date if field == "date" else cls.model.amount
        order = column.desc() if descending else column.asc()
        stmt = stmt.order_by(order, cls.model.id.desc()).offset(offset).limit(limit)
        result = await session.execute(stmt)
        return list(result.scalars().unique().all())

    @classmethod
    async def count_filtered(cls, session: AsyncSession, user_id, **filters) -> int:
        filters = await cls._expand_categories(session, user_id, filters)
        subquery = (
            cls._filtered_stmt(user_id=user_id, **filters).order_by(None).subquery()
        )
        stmt = select(func.count()).select_from(subquery)
        result = await session.execute(stmt)
        return int(result.scalar() or 0)

    @classmethod
    async def sum_filtered(cls, session: AsyncSession, user_id, **filters) -> float:
        filters = await cls._expand_categories(session, user_id, filters)
        subquery = (
            cls._filtered_stmt(user_id=user_id, **filters).order_by(None).subquery()
        )
        stmt = select(func.coalesce(func.sum(subquery.c.amount), 0.0))
        result = await session.execute(stmt)
        return float(result.scalar() or 0.0)

    @classmethod
    async def sum_by_category(
        cls,
        session: AsyncSession,
        user_id,
        transaction_type: Optional[TransactionType] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Sequence:
        stmt = (
            select(
                CategoryModel.id.label("category_id"),
                CategoryModel.name.label("name"),
                CategoryModel.color.label("color"),
                CategoryModel.icon.label("icon"),
                func.coalesce(func.sum(TransactionModel.amount), 0.0).label("total"),
                func.count(TransactionModel.id).label("transactions_count"),
            )
            .join(TransactionModel, TransactionModel.category_id == CategoryModel.id)
            .join(AccountModel, TransactionModel.account_id == AccountModel.id)
            .where(AccountModel.user_id == user_id)
            .group_by(
                CategoryModel.id,
                CategoryModel.name,
                CategoryModel.color,
                CategoryModel.icon,
            )
            .order_by(func.sum(TransactionModel.amount).desc())
        )
        if transaction_type is not None:
            stmt = stmt.where(TransactionModel.type == transaction_type)
        if start_date is not None:
            stmt = stmt.where(TransactionModel.date >= start_date)
        if end_date is not None:
            stmt = stmt.where(TransactionModel.date <= end_date)
        result = await session.execute(stmt)
        return result.all()

    @classmethod
    async def find_one_by_user(
        cls, session: AsyncSession, transaction_id: int, user_id
    ) -> Optional[TransactionModel]:
        stmt = (
            select(cls.model)
            .join(AccountModel, cls.model.account_id == AccountModel.id)
            .where(cls.model.id == transaction_id, AccountModel.user_id == user_id)
            .options(
                selectinload(cls.model.account),
                selectinload(cls.model.transfer_account),
                selectinload(cls.model.tags),
            )
            .execution_options(populate_existing=True)
        )
        result = await session.execute(stmt)
        return result.scalars().unique().one_or_none()

    @classmethod
    async def count_by_category(cls, session: AsyncSession, category_id: int) -> int:
        stmt = select(func.count(cls.model.id)).where(
            cls.model.category_id == category_id
        )
        result = await session.execute(stmt)
        return int(result.scalar() or 0)

    @classmethod
    async def find_related_subscription(
        cls, session: AsyncSession, transaction_id: int
    ) -> Optional[SubscriptionModel]:
        stmt = select(SubscriptionModel).where(
            SubscriptionModel.transaction_id == transaction_id
        )
        result = await session.execute(stmt)
        return result.scalars().one_or_none()

    # ------------------------------------------------------------------ #
    #  Aggregates for the account card and the categories screen.
    #
    #  Analytics lives in a separate app (``src/analytics``) with its own
    #  queries; here is only what finance itself needs. The duplication is
    #  intentional: finance is the source of truth and must not depend on
    #  analytics.
    # ------------------------------------------------------------------ #

    @classmethod
    async def _base_rate(cls, session: AsyncSession, user_id) -> float:
        """User's base currency rate with the personal override applied."""
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

    @classmethod
    def _statistics_scope(
        cls,
        user_id,
        start_date=None,
        end_date=None,
        category_type=None,
        only_statistics=True,
        base_rate: float = 1.0,
    ):
        """Slice of the user's records with amounts in the base currency."""
        divisor = base_rate if base_rate and base_rate > 0 else 1.0
        override = (
            select(UserCurrencyRateModel.rate)
            .where(
                UserCurrencyRateModel.user_id == user_id,
                UserCurrencyRateModel.code == cls.model.currency_id,
            )
            .scalar_subquery()
        )
        rate = func.coalesce(override, CurrencyModel.exchange_rate_to_base)
        amount_base = cls.model.amount * rate / divisor
        stmt = (
            select(
                cls.model.id.label("id"),
                cls.model.date.label("date"),
                cls.model.type.label("type"),
                cls.model.category_id.label("category_id"),
                cls.model.account_id.label("account_id"),
                AccountModel.name.label("account_name"),
                AccountModel.currency_id.label("account_currency_id"),
                CategoryModel.name.label("category_name"),
                CategoryModel.color.label("category_color"),
                CategoryModel.icon.label("category_icon"),
                CategoryModel.parent_id.label("category_parent_id"),
                CategoryModel.type.label("category_type"),
                amount_base.label("amount_base"),
            )
            .select_from(cls.model)
            .join(AccountModel, cls.model.account_id == AccountModel.id)
            .join(CategoryModel, cls.model.category_id == CategoryModel.id)
            .join(CurrencyModel, cls.model.currency_id == CurrencyModel.code)
            .where(
                AccountModel.user_id == user_id,
                cls.model.type != TransactionType.TRANSFER,
            )
        )
        if only_statistics:
            stmt = stmt.where(
                AccountModel.is_excluded.is_(False), cls.model.is_excluded.is_(False)
            )
        if start_date is not None:
            stmt = stmt.where(cls.model.date >= start_date)
        if end_date is not None:
            stmt = stmt.where(cls.model.date <= end_date)
        if category_type is not None:
            stmt = stmt.where(cls.model.type == TransactionType(category_type.value))
        return stmt.subquery()

    @classmethod
    async def totals_by_account(
        cls,
        session: AsyncSession,
        user_id,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        only_statistics: bool = True,
    ) -> List:
        """Turnover by accounts for the period."""
        base_rate = await cls._base_rate(session, user_id)
        scope = cls._statistics_scope(
            user_id,
            start_date,
            end_date,
            only_statistics=only_statistics,
            base_rate=base_rate,
        )
        income = func.coalesce(
            func.sum(
                case(
                    (scope.c.type == TransactionType.INCOME, scope.c.amount_base),
                    else_=0.0,
                )
            ),
            0.0,
        )
        expense = func.coalesce(
            func.sum(
                case(
                    (scope.c.type == TransactionType.EXPENSE, scope.c.amount_base),
                    else_=0.0,
                )
            ),
            0.0,
        )
        stmt = (
            select(
                scope.c.account_id.label("account_id"),
                scope.c.account_name.label("name"),
                scope.c.account_currency_id.label("currency_id"),
                income.label("income"),
                expense.label("expense"),
                func.count(scope.c.id).label("count"),
            )
            .group_by(
                scope.c.account_id, scope.c.account_name, scope.c.account_currency_id
            )
            .order_by(func.sum(scope.c.amount_base).desc())
        )
        result = await session.execute(stmt)
        return list(result.all())

    @classmethod
    async def totals_by_category(
        cls,
        session: AsyncSession,
        user_id,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        category_type: Optional[CategoryType] = None,
        only_statistics: bool = True,
    ) -> List:
        """Totals by categories for the period."""
        base_rate = await cls._base_rate(session, user_id)
        scope = cls._statistics_scope(
            user_id,
            start_date,
            end_date,
            category_type=category_type,
            only_statistics=only_statistics,
            base_rate=base_rate,
        )
        total = func.coalesce(func.sum(scope.c.amount_base), 0.0).label("total")
        stmt = (
            select(
                scope.c.category_id.label("group_id"),
                scope.c.category_name.label("name"),
                scope.c.category_color.label("color"),
                scope.c.category_icon.label("icon"),
                scope.c.category_parent_id.label("parent_id"),
                scope.c.category_type.label("category_type"),
                total,
                func.count(scope.c.id).label("count"),
            )
            .group_by(
                scope.c.category_id,
                scope.c.category_name,
                scope.c.category_color,
                scope.c.category_icon,
                scope.c.category_parent_id,
                scope.c.category_type,
            )
            .order_by(total.desc())
        )
        result = await session.execute(stmt)
        return list(result.all())

    @classmethod
    async def find_many_by_user(
        cls, session: AsyncSession, user_id, ids: Sequence[int]
    ) -> List[TransactionModel]:
        """User records by a list of ids (for bulk operations)."""
        stmt = cls._filtered_stmt(user_id=user_id).where(cls.model.id.in_(list(ids)))
        result = await session.execute(stmt)
        return list(result.scalars().unique().all())


class UserCurrencyRateDAO(BaseDAO[UserCurrencyRateModel, dict, dict]):
    """User's personal currency rates."""

    model = UserCurrencyRateModel

    @classmethod
    async def find_all_by_user(
        cls, session: AsyncSession, user_id
    ) -> List[UserCurrencyRateModel]:
        stmt = select(cls.model).where(cls.model.user_id == user_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def find_one(
        cls, session: AsyncSession, user_id, code: str
    ) -> Optional[UserCurrencyRateModel]:
        stmt = select(cls.model).where(
            cls.model.user_id == user_id, cls.model.code == code.upper()
        )
        result = await session.execute(stmt)
        return result.scalars().one_or_none()


class SubscriptionDAO(
    BaseDAO[SubscriptionModel, SubscriptionCreate, SubscriptionUpdate]
):
    model = SubscriptionModel

    @classmethod
    def _filtered_stmt(cls, user_id, is_active: Optional[bool] = None) -> Select:
        stmt = (
            select(cls.model)
            .join(TransactionModel, cls.model.transaction_id == TransactionModel.id)
            .join(AccountModel, TransactionModel.account_id == AccountModel.id)
            .where(AccountModel.user_id == user_id)
            .options(selectinload(cls.model.transaction))
        )
        if is_active is not None:
            stmt = stmt.where(cls.model.is_active.is_(is_active))
        return stmt

    @classmethod
    async def find_all_by_user(
        cls,
        session: AsyncSession,
        user_id,
        is_active: Optional[bool] = None,
        offset: int = 0,
        limit: int = 100,
    ) -> List[SubscriptionModel]:
        stmt = (
            cls._filtered_stmt(user_id=user_id, is_active=is_active)
            .order_by(cls.model.next_payment_date)
            .offset(offset)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().unique().all())

    @classmethod
    async def find_one_by_user(
        cls, session: AsyncSession, subscription_id: int, user_id
    ) -> Optional[SubscriptionModel]:
        stmt = cls._filtered_stmt(user_id=user_id).where(
            cls.model.id == subscription_id
        )
        result = await session.execute(stmt)
        return result.scalars().unique().one_or_none()

    @classmethod
    async def find_upcoming(
        cls,
        session: AsyncSession,
        user_id,
        before: datetime,
        offset: int = 0,
        limit: int = 100,
    ) -> List[SubscriptionModel]:
        stmt = (
            cls._filtered_stmt(user_id=user_id, is_active=True)
            .where(cls.model.next_payment_date <= before)
            .order_by(cls.model.next_payment_date)
            .offset(offset)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().unique().all())
