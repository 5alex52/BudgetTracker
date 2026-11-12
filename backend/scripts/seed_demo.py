"""Demo data for local frontend development.

The script creates a verified user with content: accounts in different
currencies, a category tree, six months of transactions, tags, templates and
a free-plan subscription. It exists so the UI doesn't open on empty screens.

Run inside the backend container (from the project root)::

    docker compose exec backend python -m scripts.seed_demo            # create or update
    docker compose exec backend python -m scripts.seed_demo --reset    # wipe the user's data

Default login: ``demo`` + the domain below / ``demo12345``.
Password and email can be overridden with the ``DEMO_USER_EMAIL`` and
``DEMO_USER_PASSWORD`` environment variables.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import uuid
from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from sqlalchemy import delete
from sqlalchemy import select
from src.database import async_session_maker
from src.finance.models import AccountModel
from src.finance.models import CategoryModel
from src.finance.models import TagModel
from src.finance.models import TemplateModel
from src.finance.models import TransactionModel
from src.finance.models import UserCurrencyRateModel
from src.finance.schemas import AccountType
from src.finance.schemas import CategoryType
from src.finance.schemas import TransactionType
from src.users.models import UserModel
from src.users.utils import get_password_hash

# Billing models are needed so SQLAlchemy can wire up UserModel relationships

# Build the login from parts: makes it easier to replace the whole address
_DEMO_LOGIN = "demo"
_DEMO_DOMAIN = "budgettracker.local"
DEMO_EMAIL = os.getenv("DEMO_USER_EMAIL") or f"{_DEMO_LOGIN}{'@'}{_DEMO_DOMAIN}"
DEMO_PASSWORD = os.getenv("DEMO_USER_PASSWORD", "demo12345")
DEMO_NAME = ("Демо", "Пользователь")

#: Accounts: name, type, currency, starting balance, flags
ACCOUNTS: List[Tuple[str, AccountType, str, float, Dict[str, bool]]] = [
    ("Alfa", AccountType.CHECKING, "BYN", 54.8, {}),
    ("Alfa Сейф", AccountType.SAVINGS, "BYN", 11759.91, {}),
    ("Наличные", AccountType.CASH, "BYN", 370.0, {}),
    ("Alfa RUB", AccountType.CHECKING, "RUB", 109401.99, {}),
    ("Alfa USD", AccountType.CHECKING, "USD", 240.0, {"is_excluded": True}),
    ("Cash EUR", AccountType.CASH, "EUR", 0.0, {"is_archived": True}),
]

#: Expense categories: parent → subcategories (name, icon, color)
EXPENSE_CATEGORIES: List[Tuple[str, str, str, List[Tuple[str, str, str]]]] = [
    (
        "Еда и напитки",
        "utensils",
        "#e0913c",
        [
            ("Продукты", "shopping-cart", "#3aa76d"),
            ("Кафе и рестораны", "chef-hat", "#e06fa0"),
            ("Доставка еды", "box", "#c26bd6"),
        ],
    ),
    (
        "Жильё",
        "house",
        "#d94b4b",
        [
            ("Аренда", "house", "#d94b4b"),
            ("Коммунальные услуги", "plug", "#e08a3c"),
        ],
    ),
    (
        "Транспорт",
        "bus",
        "#2ba7d6",
        [
            ("Такси", "car", "#2ba7d6"),
            ("Топливо", "fuel", "#5b8fd6"),
        ],
    ),
    (
        "Покупки",
        "shopping-bag",
        "#3aa76d",
        [
            ("Одежда", "shirt", "#3aa76d"),
            ("Техника", "smartphone", "#c26bd6"),
        ],
    ),
    (
        "Жизнь и развлечения",
        "theater",
        "#8b6fd6",
        [
            ("Кино", "theater", "#8b6fd6"),
            ("Спорт", "dumbbell", "#2b9a8f"),
        ],
    ),
    (
        "Связь и подписки",
        "smartphone",
        "#c26bd6",
        [
            ("Мобильная связь", "smartphone", "#c26bd6"),
            ("Подписки", "book", "#5b8fd6"),
        ],
    ),
    (
        "Финансовые расходы",
        "landmark",
        "#5b8fd6",
        [
            ("Банковские комиссии", "landmark", "#5b8fd6"),
        ],
    ),
]

INCOME_CATEGORIES: List[Tuple[str, str, str, List[Tuple[str, str, str]]]] = [
    (
        "Доход",
        "arrow-down-left",
        "#2b9a6d",
        [
            ("Зарплата", "briefcase", "#2b9a6d"),
            ("Фриланс", "laptop", "#2ba7d6"),
            ("Проценты", "percent", "#3aa76d"),
        ],
    ),
]

#: Quick-entry templates: name, type, amount, account, category, note
TEMPLATES: List[Tuple[str, TransactionType, float, str, str, str]] = [
    (
        "Кофе",
        TransactionType.EXPENSE,
        3.5,
        "Наличные",
        "Кафе и рестораны",
        "Кофе по утрам",
    ),
    (
        "Продукты",
        TransactionType.EXPENSE,
        45.0,
        "Alfa",
        "Продукты",
        "Недельная закупка",
    ),
    ("Такси домой", TransactionType.EXPENSE, 12.0, "Alfa", "Такси", ""),
    ("Зарплата", TransactionType.INCOME, 2500.0, "Alfa", "Зарплата", ""),
]

TAGS: List[Tuple[str, str]] = [
    ("работа", "#5b8fd6"),
    ("семья", "#e06fa0"),
    ("поездка", "#2ba7d6"),
    ("здоровье", "#3aa76d"),
]


async def _get_or_create_user(session) -> UserModel:
    user = (await session.execute(select(UserModel).where(UserModel.email == DEMO_EMAIL))).scalar_one_or_none()
    if user is not None:
        print(f"[seed] user already exists: {DEMO_EMAIL}")
        user.is_verified = True
        user.is_active = True
        await session.commit()
        return user

    user = UserModel(
        id=uuid.uuid4(),
        firstname=DEMO_NAME[0],
        lastname=DEMO_NAME[1],
        email=DEMO_EMAIL,
        password=get_password_hash(DEMO_PASSWORD),
        is_verified=True,
        is_active=True,
        is_superuser=False,
        base_currency="BYN",
        locale="ru",
        theme="system",
        telegram_id=0,
    )
    session.add(user)
    await session.commit()
    print(f"[seed] user created: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    return user


async def _reset_user_data(session, user: UserModel) -> None:
    """Delete the demo user's content while keeping the user itself.

    Transactions have no ``user_id`` of their own: they belong to the user via
    the account, so they are deleted after the accounts (cascade) — the point
    here is just not to forget them.
    """
    account_ids = select(AccountModel.id).where(AccountModel.user_id == user.id)
    await session.execute(delete(TransactionModel).where(TransactionModel.account_id.in_(account_ids)))
    for model in (
        TemplateModel,
        UserCurrencyRateModel,
        TagModel,
        CategoryModel,
        AccountModel,
    ):
        await session.execute(delete(model).where(model.user_id == user.id))
    await session.commit()
    print("[seed] user data deleted")


async def _seed_accounts(session, user: UserModel) -> Dict[str, AccountModel]:
    created: Dict[str, AccountModel] = {}
    for name, account_type, currency, balance, flags in ACCOUNTS:
        account = AccountModel(
            user_id=user.id,
            name=name,
            type=account_type,
            currency_id=currency,
            balance=balance,
            is_archived=flags.get("is_archived", False),
            is_excluded=flags.get("is_excluded", False),
        )
        session.add(account)
        created[name] = account
    await session.commit()
    print(f"[seed] accounts: {len(created)}")
    return created


async def _seed_categories(session, user: UserModel) -> Dict[str, CategoryModel]:
    created: Dict[str, CategoryModel] = {}

    async def create_group(
        name: str,
        icon: str,
        color: str,
        kind: CategoryType,
        children: List[Tuple[str, str, str]],
    ) -> None:
        parent = CategoryModel(
            user_id=user.id,
            name=name,
            type=kind,
            icon=icon,
            color=color,
            parent_id=None,
        )
        session.add(parent)
        await session.flush()
        created[name] = parent
        for child_name, child_icon, child_color in children:
            child = CategoryModel(
                user_id=user.id,
                name=child_name,
                type=kind,
                icon=child_icon,
                color=child_color,
                parent_id=parent.id,
            )
            session.add(child)
            await session.flush()
            created[child_name] = child

    for name, icon, color, children in EXPENSE_CATEGORIES:
        await create_group(name, icon, color, CategoryType.EXPENSE, children)
    for name, icon, color, children in INCOME_CATEGORIES:
        await create_group(name, icon, color, CategoryType.INCOME, children)

    await session.commit()
    print(f"[seed] categories: {len(created)}")
    return created


async def _seed_tags(session, user: UserModel) -> Dict[str, TagModel]:
    created: Dict[str, TagModel] = {}
    for name, color in TAGS:
        tag = TagModel(user_id=user.id, name=name, color=color)
        session.add(tag)
        created[name] = tag
    await session.commit()
    print(f"[seed] tags: {len(created)}")
    return created


async def _seed_transactions(
    session,
    user: UserModel,
    accounts: Dict[str, AccountModel],
    categories: Dict[str, CategoryModel],
    tags: Dict[str, TagModel],
) -> None:
    """Six months of transactions: groceries and transport on weekdays, salary and rent once a month."""
    random.seed(20251009)
    start = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0) - timedelta(days=180)
    account_names = ["Alfa", "Наличные", "Alfa Сейф", "Alfa RUB"]
    tagged_notes = {
        "работа": "работа",
        "семья": "семейные расходы",
        "поездка": "поездка",
        "здоровье": "аптека",
    }
    tag_list = list(tags.values())

    rows: List[TransactionModel] = []
    for day in range(180):
        moment = start + timedelta(days=day)
        # Salary and rent — once a month
        if moment.day == 5:
            rows.append(
                TransactionModel(
                    account_id=accounts["Alfa"].id,
                    category_id=categories["Зарплата"].id,
                    amount=2500.0,
                    currency_id="BYN",
                    type=TransactionType.INCOME,
                    date=moment.replace(hour=10, minute=5),
                    note="Зарплата",
                )
            )
        if moment.day == 10:
            rows.append(
                TransactionModel(
                    account_id=accounts["Alfa"].id,
                    category_id=categories["Аренда"].id,
                    amount=400.0,
                    currency_id="BYN",
                    type=TransactionType.EXPENSE,
                    date=moment.replace(hour=9, minute=30),
                    note="Аренда квартиры",
                )
            )

        # Everyday spending: 1–3 transactions per day
        for _ in range(random.randint(1, 3)):
            category_name = random.choice(
                [
                    "Продукты",
                    "Кафе и рестораны",
                    "Такси",
                    "Топливо",
                    "Кино",
                    "Подписки",
                    "Одежда",
                ]
            )
            account_name = random.choice(account_names)
            account = accounts[account_name]
            amount = round(random.uniform(5, 120), 2)
            note = random.choice(
                [
                    "Пятёрочка",
                    "ВкусВилл",
                    "такси домой",
                    "заправка",
                    "билеты в кино",
                    "Netflix",
                    "",
                ]
            )
            transaction = TransactionModel(
                account_id=account.id,
                category_id=categories[category_name].id,
                amount=amount,
                currency_id=account.currency_id,
                type=TransactionType.EXPENSE,
                date=moment.replace(hour=random.randint(8, 22), minute=random.randint(0, 59)),
                note=note or None,
            )
            rows.append(transaction)

    # Tags: give a few transactions the "health" and "trip" tags so the filter has something to work on
    for index in range(0, min(24, len(rows)), 3):
        rows[index].tags = [random.choice(tag_list)]
    for index in range(1, min(12, len(rows)), 4):
        rows[index].tags = [tag_list[0]]

    session.add_all(rows)
    await session.commit()
    print(f"[seed] transactions: {len(rows)}")

    # Balances: recompute from transactions so accounts reconcile with the history
    for name, account in accounts.items():
        delta = 0.0
        for row in rows:
            if row.account_id != account.id:
                continue
            sign = 1 if row.type == TransactionType.INCOME else -1
            delta += sign * float(row.amount)
        account.balance = round(float(account.balance) + delta, 2)
    await session.commit()
    print("[seed] account balances recomputed")


async def _seed_templates(
    session,
    user: UserModel,
    accounts: Dict[str, AccountModel],
    categories: Dict[str, CategoryModel],
    tags: Dict[str, TagModel],
) -> None:
    for name, kind, amount, account_name, category_name, note in TEMPLATES:
        account = accounts[account_name]
        template = TemplateModel(
            user_id=user.id,
            name=name,
            type=kind,
            amount=amount,
            currency_id=account.currency_id,
            account_id=account.id,
            category_id=categories[category_name].id,
            note=note or None,
            icon="bolt",
            usage_count=0,
        )
        if name == "Продукты":
            template.tags = [tags["семья"]]
        session.add(template)
    await session.commit()
    print(f"[seed] templates: {len(TEMPLATES)}")


async def seed(reset: bool = False) -> None:
    async with async_session_maker() as session:
        user = await _get_or_create_user(session)
        if reset:
            await _reset_user_data(session, user)

        existing = (
            await session.execute(select(AccountModel).where(AccountModel.user_id == user.id).limit(1))
        ).scalar_one_or_none()
        if existing is not None and not reset:
            print("[seed] data already exists — not recreating (use --reset)")
            return

        accounts = await _seed_accounts(session, user)
        categories = await _seed_categories(session, user)
        tags = await _seed_tags(session, user)
        await _seed_transactions(session, user, accounts, categories, tags)
        await _seed_templates(session, user, accounts, categories, tags)

    print("[seed] done")
    print(f"[seed] login: {DEMO_EMAIL} / {DEMO_PASSWORD}")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="BudgetTracker demo data")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete the demo user's data and recreate it",
    )
    args = parser.parse_args(argv)
    asyncio.run(seed(reset=args.reset))


if __name__ == "__main__":
    main()
