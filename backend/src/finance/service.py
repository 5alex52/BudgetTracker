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
from .rules import apply_rules
from .schemas import AccountCreate
from .schemas import AccountSummary
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
    """Код базовой валюты пользователя (верхний регистр)."""
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


class CurrencyService(BaseService[CurrencyModel, CurrencyCreate, CurrencyUpdate]):
    dao = CurrencyDAO

    @classmethod
    async def _user_base_currency(cls, session_maker: Optional[async_sessionmaker], user_id) -> str:
        """Код базовой валюты пользователя; "USD" — если настройка не задана."""
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
        # Базовая валюта — личная настройка пользователя; "USD" остаётся запасным
        # вариантом для анонимных запросов справочника.
        if base is None and user_id is not None:
            base = await CurrencyService._user_base_currency(session_maker, user_id)
        base = (base or "USD").upper()
        """Курсы всех валют относительно выбранной базовой.

        В справочнике хранится «сколько базовых единиц стоит одна единица валюты»,
        а экран «Валюты» показывает обратное — «сколько единиц валюты за одну базовую»,
        поэтому курс переворачивается через базовую валюту.
        """
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            currencies = await cls.dao.find_all_ordered(session, limit=500)
            # Личные курсы переопределяют справочник: пользователь может считать по своему банку
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
        """Личный курс валюты: «сколько базовых единиц стоит одна единица валюты»."""
        if rate <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rate must be positive")
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            currency = await cls.dao.find_one_or_none(session, code=code.upper())
            if currency is None:
                raise _not_found("Currency not found")
            await _check_currency_settings_entitlement(session, user_id, currency.code, session_maker=maker)
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
        """Возврат к курсу справочника."""
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
    """Сбрасывает кеш аналитики: цифры на «Обзоре» зависят от записей и счетов."""
    from ..cache import Cache

    await Cache.delete_scope("analytics")


async def _invalidate_categories() -> None:
    """Сбрасывает кеш категорий: дерево и список меняются при любом изменении."""
    from ..cache import Cache

    await Cache.delete_scope("categories")


async def _check_account_limit(session, user_id, session_maker=None) -> None:
    """Не даёт превысить лимит счетов бесплатного тарифа.

    Импорт биллинга ленивый: финансовый модуль не должен зависеть от него на
    этапе импорта, иначе получается цикл ``billing -> finance``.
    """
    from src.billing.service import BillingService

    entitlements = await BillingService.get_entitlements(user_id, session_maker=session_maker)
    if entitlements.max_accounts is None:
        return
    # Лимит тарифа считается по всем незаархивированным счетам: заблокированные
    # счета в другой валюте всё равно остаются заведёнными, просто без доступа.
    existing = await AccountDAO.count_by_user(session, user_id)
    if existing >= entitlements.max_accounts:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Account limit reached: the {entitlements.plan_name} plan allows "
                f"{entitlements.max_accounts} accounts. Upgrade to add more."
            ),
        )


async def _check_currency_entitlement(session, user_id, currency_id: str, session_maker=None) -> None:
    """На бесплатном тарифе счёт можно вести только в базовой валюте.

    Существующие счета в других валютах не удаляются — они просто остаются
    заблокированными до обновления подписки (``multi_currency``).
    """
    from src.billing.service import BillingService
    from ..users.models import UserModel

    entitlements = await BillingService.get_entitlements(user_id, session_maker=session_maker)
    if entitlements.multi_currency:
        return
    base = await _resolve_base_code(session, user_id)
    if (currency_id or "").upper() != base:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"The {entitlements.plan_name} plan allows accounts only in the base currency "
                f"({base}). Upgrade to use other currencies."
            ),
        )


LOCK_REASON_CURRENCY = "subscription_required_currency"
LOCK_REASON_ACCOUNT_LIMIT = "subscription_required_account_limit"


async def _get_entitlements(user_id, session_maker=None):
    """Права тарифа. Импорт ленивый, чтобы не было цикла billing ↔ finance."""
    from src.billing.service import BillingService

    return await BillingService.get_entitlements(user_id, session_maker=session_maker)


async def _account_lock_map(
    session: AsyncSession,
    user_id,
    session_maker=None,
    entitlements=None,
) -> dict:
    """Какие счета доступны только на чтение и почему.

    На бесплатном тарифе действуют два ограничения: только базовая валюта и
    не больше ``max_accounts`` счетов. Счета сверх лимита и счета в других
    валютах не удаляются и не архивируются — они остаются в списке, но
    помечаются заблокированными до возобновления подписки.
    """
    if entitlements is None:
        entitlements = await _get_entitlements(user_id, session_maker=session_maker)
    base = await _resolve_base_code(session, user_id)
    accounts = await AccountDAO.find_all_by_user(
        session,
        user_id,
        include_archived=False,
        include_excluded=True,
        limit=500,
    )
    locks: dict = {}
    used = 0
    for account in sorted(accounts, key=lambda item: item.id):
        currency = (account.currency_id or "").upper()
        if not entitlements.multi_currency and currency != base:
            locks[account.id] = (True, LOCK_REASON_CURRENCY)
            continue
        if entitlements.max_accounts is not None and used >= entitlements.max_accounts:
            locks[account.id] = (True, LOCK_REASON_ACCOUNT_LIMIT)
        else:
            locks[account.id] = (False, None)
            used += 1
    return locks


def _apply_account_locks(accounts: List[AccountModel], locks: dict) -> None:
    """Проставляет вычисляемые флаги блокировки на ORM-объекты для ответа API."""
    for account in accounts:
        locked, reason = locks.get(account.id, (False, None))
        account.is_locked = locked
        account.lock_reason = reason


async def _effective_currency_rate(session: AsyncSession, user_id, code: str) -> float:
    """Курс валюты с личным переопределением пользователя."""
    currency = await _get_currency(session, code)
    override = await UserCurrencyRateDAO.find_one(session, user_id, currency.code)
    rate = override.rate if override is not None else currency.exchange_rate_to_base
    return float(rate) if rate and rate > 0 else 1.0


async def _check_transaction_entitlement(
    session: AsyncSession,
    user_id,
    account: AccountModel,
    currency_id: str,
    session_maker=None,
) -> None:
    """Проверяет, можно ли писать запись на счёт в выбранной валюте.

    На бесплатном тарифе доступны только базовая валюта и незаблокированные
    счета. Проверка стоит на создании/изменении записи и при применении
    шаблона, чтобы ограничение нельзя было обойти через другой эндпоинт.
    """
    entitlements = await _get_entitlements(user_id, session_maker=session_maker)
    core_currency = (currency_id or "").upper()
    if not entitlements.multi_currency:
        base = await _resolve_base_code(session, user_id)
        if core_currency != base:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    f"The {entitlements.plan_name} plan allows records only in the "
                    f"base currency ({base}). Upgrade to use other currencies."
                ),
            )
    locks = await _account_lock_map(
        session,
        user_id,
        session_maker=session_maker,
        entitlements=entitlements,
    )
    locked, reason = locks.get(account.id, (False, None))
    if locked:
        hint = (
            "the account currency is available on a paid plan"
            if reason == LOCK_REASON_CURRENCY
            else "the free plan account limit is exceeded"
        )
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(f"Account is read-only until the subscription is renewed: {hint}."),
        )


async def _check_currency_settings_entitlement(
    session: AsyncSession,
    user_id,
    code: str,
    session_maker=None,
) -> None:
    """Бесплатный тариф не даёт настраивать курсы других валют."""
    entitlements = await _get_entitlements(user_id, session_maker=session_maker)
    if entitlements.multi_currency:
        return
    base = await _resolve_base_code(session, user_id)
    if (code or "").upper() != base:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"The {entitlements.plan_name} plan allows only the base currency "
                f"({base}). Upgrade to use multiple currencies."
            ),
        )


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
            locks = await _account_lock_map(session, user_id, session_maker=maker)
            _apply_account_locks(accounts, locks)
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
            locks = await _account_lock_map(session, user_id, session_maker=maker)
            _apply_account_locks([account], locks)
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
            await _check_account_limit(session, user_id, session_maker=maker)
            await _check_currency_entitlement(session, user_id, schema.currency_id, session_maker=maker)
            account = await cls.dao.create(session, {**schema.model_dump(), "user_id": user_id})
            if account is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Account creation conflict",
                )
            await session.commit()
            locks = await _account_lock_map(session, user_id, session_maker=maker)
            _apply_account_locks([account], locks)
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
            locks = await _account_lock_map(session, user_id, session_maker=maker)
            locked, _ = locks.get(account.id, (False, None))
            # Заблокированный счёт можно только архивировать/исключать:
            # остальные поля доступны после возобновления подписки.
            if locked and any(field not in {"is_archived", "is_excluded"} for field in update_data):
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=("Account is read-only until the subscription is renewed."),
                )
            if "currency_id" in update_data:
                await _get_currency(session, update_data["currency_id"])
                await _check_currency_entitlement(session, user_id, update_data["currency_id"], session_maker=maker)
            for field, value in update_data.items():
                setattr(account, field, value)
            await session.commit()
            locks = await _account_lock_map(session, user_id, session_maker=maker)
            _apply_account_locks([account], locks)
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
            # Архивация меняет число активных счетов: у следующих по порядку
            # может появиться или пропасть блокировка по лимиту тарифа.
            locks = await _account_lock_map(session, user_id, session_maker=maker)
            _apply_account_locks([account], locks)
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
        """Флаг «исключён из статистики»: счёт остаётся, но не влияет на итоги."""
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            account = await _get_owned_account(session, account_id, user_id)
            account.is_excluded = is_excluded
            await session.commit()
            # refresh нужен до закрытия сессии: updated_at считается на стороне БД,
            # и без него сериализация ответа пытается дочитать объект вне сессии
            await session.refresh(account)
            locks = await _account_lock_map(session, user_id, session_maker=maker)
            _apply_account_locks([account], locks)
        # Исключённый счёт выпадает из всех итогов и графиков
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
        """Карточка счёта: остаток и обороты за период в базовой валюте."""
        start_date, end_date = normalize_period(start_date, end_date)
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            account = await _get_owned_account(session, account_id, user_id)
            # Обороты считаем по всем счетам и берём нужный: один запрос дешевле,
            # чем отдельная выборка под каждый счёт.
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

            # Остаток «как в банке»: на конец периода, а не текущий.
            # Текущий остаток минус всё, что случилось позже конца периода.
            later = 0.0
            if end_date is not None:
                deltas = await TransactionDAO.signed_totals_after_by_account(
                    session, user_id, end_date, account_ids=[account.id]
                )
                later = deltas.get(account.id, 0.0)

            locks = await _account_lock_map(session, user_id, session_maker=maker)
            is_locked, lock_reason = locks.get(account.id, (False, None))

        return AccountSummary(
            account_id=account.id,
            name=account.name,
            currency_id=account.currency_id,
            balance=round(float(account.balance) - later, 2),
            is_archived=account.is_archived,
            is_excluded=account.is_excluded,
            is_locked=is_locked,
            lock_reason=lock_reason,
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
        """Остатки по счетам в базовой валюте.

        ``end_date`` включает «банковский» режим: остаток берётся на конец
        периода (текущий остаток минус всё, что произошло позже), поэтому при
        переключении периода виджет показывает цифру того момента, а не сегодняшнюю.
        """
        maker = _resolve_session_maker(session_maker)
        async with maker() as session:
            # Исключённые из статистики счета не участвуют в общем балансе
            accounts = await cls.dao.find_all_by_user(
                session,
                user_id,
                include_archived=False,
                include_excluded=False,
                limit=500,
            )
            later: dict = {}
            if end_date is not None and accounts:
                later = await TransactionDAO.signed_totals_after_by_account(
                    session,
                    user_id,
                    end_date,
                    account_ids=[account.id for account in accounts],
                )

            # Общий итог считается в базовой валюте пользователя, а не в USD.
            # Личные курсы переопределяют справочник — иначе итог на дашборде
            # расходится с экраном «Валюты».
            base_rate = await _resolve_base_rate(session, user_id)
            overrides = {
                row.code: float(row.rate)
                for row in await UserCurrencyRateDAO.find_all_by_user(session, user_id)
                if row.rate and row.rate > 0
            }
            locks = await _account_lock_map(session, user_id, session_maker=maker)

            items: List[BalanceOverviewAccount] = []
            total = 0.0
            for account in accounts:
                balance = round(float(account.balance) - later.get(account.id, 0.0), 2)
                currency_rate = overrides.get(
                    (account.currency_id or "").upper(),
                    float(account.currency.exchange_rate_to_base),
                )
                balance_base = convert_amount(balance, currency_rate, base_rate)
                is_locked, lock_reason = locks.get(account.id, (False, None))
                items.append(
                    BalanceOverviewAccount(
                        account_id=account.id,
                        name=account.name,
                        currency_id=account.currency_id,
                        balance=balance,
                        balance_base=balance_base,
                        is_archived=account.is_archived,
                        is_excluded=account.is_excluded,
                        is_locked=is_locked,
                        lock_reason=lock_reason,
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
        """Создаёт стандартный набор категорий и подкатегорий.

        Вызывается один раз при регистрации: пользователь сразу получает
        привычную структуру и может её переименовать, перекрасить или удалить —
        это обычные пользовательские категории. Весь набор пишется в одной
        транзакции: либо все категории, либо ни одной.
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
        """Дерево категорий с подкатегориями и счётчиками записей.

        Настройки и диалог записи показывают категорию вместе с её подкатегориями,
        поэтому дерево собирается одним ответом: без него интерфейс делает
        N+1 запросов на каждую категорию.
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
        """Сколько записей и на какую сумму приходится на каждую категорию."""
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
        """Приводит границы периода и отбрасывает пустые значения.

        Экран «Записи» присылает пустые строки и пустые списки, когда фильтр снят:
        их нужно не применять, а не фильтровать «по пустоте».
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
        """Удаляет выбранные записи и откатывает их влияние на балансы.

        Возвращает ``(сколько удалено, какие идентификаторы не найдены)``.
        Чужие записи не трогаются: они попадают в «не найдены».
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
            category = await _get_owned_category(session, schema.category_id, user_id)
            _validate_category_type(category, schema.type)
            currency = await _get_currency(session, schema.currency_id)
            await _check_transaction_entitlement(
                session,
                user_id,
                account,
                currency.code,
                session_maker=maker,
            )

            tag_ids = schema.tag_ids
            await ensure_tags_owned(session, tag_ids, user_id)

            # tag_ids — не колонка таблицы, поэтому в insert уходит всё остальное
            transaction = await cls.dao.create(session, schema.model_dump(exclude={"tag_ids"}))
            if transaction is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Transaction creation conflict",
                )

            if tag_ids:
                await attach_tags(session, transaction.id, tag_ids)
            # Правила применяются после сохранения: им нужен id записи для связи с метками
            await apply_rules(session, transaction, user_id)

            account.balance = round(
                account.balance
                + _converted_delta(
                    schema.type,
                    schema.amount,
                    await _effective_currency_rate(session, user_id, currency.code),
                    await _effective_currency_rate(session, user_id, account.currency_id),
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
            old_delta = _converted_delta(
                transaction.type,
                transaction.amount,
                await _effective_currency_rate(session, user_id, old_currency.code),
                await _effective_currency_rate(session, user_id, old_account.currency_id),
            )

            account = old_account
            if "account_id" in update_data:
                account = await _get_owned_account(session, update_data["account_id"], user_id)

            category = transaction.category
            if "category_id" in update_data:
                category = await _get_owned_category(session, update_data["category_id"], user_id)

            new_type = update_data.get("type", transaction.type)
            new_amount = update_data.get("amount", transaction.amount)
            new_currency = await _get_currency(session, update_data.get("currency_id", transaction.currency_id))
            _validate_category_type(category, new_type)
            # Проверяем итоговый счёт и валюту записи, а не старые значения:
            # перенести запись со заблокированного счёта на доступный можно.
            await _check_transaction_entitlement(
                session,
                user_id,
                account,
                new_currency.code,
                session_maker=maker,
            )

            new_delta = _converted_delta(
                new_type,
                new_amount,
                await _effective_currency_rate(session, user_id, new_currency.code),
                await _effective_currency_rate(session, user_id, account.currency_id),
            )

            old_account.balance = round(old_account.balance - old_delta, 2)
            account.balance = round(account.balance + new_delta, 2)

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
            account.balance = round(
                account.balance
                - _converted_delta(
                    transaction.type,
                    transaction.amount,
                    await _effective_currency_rate(session, user_id, currency.code),
                    await _effective_currency_rate(session, user_id, account.currency_id),
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
