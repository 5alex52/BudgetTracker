"""Администратор со стандартными доступами для локальной разработки.

Скрипт создаёт суперпользователя с фиксированными логином и паролем либо
приводит уже существующего к ним же: почта, пароль и флаги ``is_superuser``,
``is_verified``, ``is_active`` выставляются заново. Так «стандартный пароль»
всегда восстанавливается одной командой, даже если его успели сменить.

Данные админу не создаются: это управленческая учётная запись, наполнение
для демонстрации делает ``scripts.seed_demo``.

Запуск — внутри контейнера backend (из корня проекта)::

    docker compose exec backend python -m scripts.seed_admin
    docker compose exec backend python -m scripts.seed_admin --keep-password   # не менять пароль

Логин по умолчанию: ``admin`` + домен ниже / ``admin12345``.
Почту и пароль можно переопределить переменными окружения
``ADMIN_USER_EMAIL`` и ``ADMIN_USER_PASSWORD``.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import uuid
from typing import List
from typing import Optional

from sqlalchemy import select
from src.billing import models as _billing_models  # noqa: F401
from src.database import async_session_maker
from src.finance import models as _finance_models  # noqa: F401
from src.users.models import UserModel
from src.users.utils import get_password_hash

# Модели финансов и биллинга нужны, чтобы SQLAlchemy связал relationship'ы UserModel

# Логин собираем из частей: так адрес проще заменить целиком
_ADMIN_LOGIN = "admin"
_ADMIN_DOMAIN = "budgettracker.local"
ADMIN_EMAIL = os.getenv("ADMIN_USER_EMAIL") or f"{_ADMIN_LOGIN}{'@'}{_ADMIN_DOMAIN}"
ADMIN_PASSWORD = os.getenv("ADMIN_USER_PASSWORD", "admin12345")
ADMIN_NAME = ("Администратор", "BudgetTracker")


async def seed_admin(keep_password: bool = False) -> None:
    async with async_session_maker() as session:
        user = (
            await session.execute(
                select(UserModel).where(UserModel.email == ADMIN_EMAIL)
            )
        ).scalar_one_or_none()

        if user is None:
            user = UserModel(
                id=uuid.uuid4(),
                firstname=ADMIN_NAME[0],
                lastname=ADMIN_NAME[1],
                email=ADMIN_EMAIL,
                password=get_password_hash(ADMIN_PASSWORD),
                is_verified=True,
                is_active=True,
                is_superuser=True,
                base_currency="BYN",
                locale="ru",
                theme="system",
                # Колонка уникальная и NOT NULL: 0 занят демо-пользователем,
                # отрицательный id не может совпасть с настоящим Telegram
                telegram_id=-1,
            )
            session.add(user)
            await session.commit()
            print(f"[admin] создан суперпользователь {ADMIN_EMAIL}")
        else:
            # Почта могла быть изменена — возвращаем стандартную
            user.email = ADMIN_EMAIL
            user.is_superuser = True
            user.is_verified = True
            user.is_active = True
            if not keep_password:
                user.password = get_password_hash(ADMIN_PASSWORD)
            await session.commit()
            print(f"[admin] обновлён суперпользователь {ADMIN_EMAIL}")

    print("[admin] готово")
    print(
        f"[admin] вход: {ADMIN_EMAIL} / "
        + ("пароль не менялся" if keep_password else ADMIN_PASSWORD)
    )


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Администратор BudgetTracker со стандартными доступами"
    )
    parser.add_argument(
        "--keep-password",
        action="store_true",
        help="не сбрасывать пароль существующего пользователя на стандартный",
    )
    args = parser.parse_args(argv)
    asyncio.run(seed_admin(keep_password=args.keep_password))


if __name__ == "__main__":
    main()
