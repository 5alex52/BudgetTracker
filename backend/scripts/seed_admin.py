"""Administrator with default credentials for local development.

The script creates a superuser with a fixed login and password, or brings an
existing one back to them: email, password and the ``is_superuser``,
``is_verified``, ``is_active`` flags are set anew. This way the "default
password" can always be restored with a single command, even if it was changed.

No data is created for the admin: it is a management account; demo content
is seeded by ``scripts.seed_demo``.

Run inside the backend container (from the project root)::

    docker compose exec backend python -m scripts.seed_admin
    docker compose exec backend python -m scripts.seed_admin --keep-password   # keep the password

Default login: ``admin`` + the domain below / ``admin12345``.
Email and password can be overridden with the ``ADMIN_USER_EMAIL`` and
``ADMIN_USER_PASSWORD`` environment variables.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import uuid
from typing import List
from typing import Optional

from sqlalchemy import select
from src.database import async_session_maker
from src.finance import models as _finance_models  # noqa: F401
from src.users.models import UserModel
from src.users.utils import get_password_hash

# Finance and billing models are needed so SQLAlchemy can wire up UserModel relationships

# Build the login from parts: makes it easier to replace the whole address
_ADMIN_LOGIN = "admin"
_ADMIN_DOMAIN = "budgettracker.local"
ADMIN_EMAIL = os.getenv("ADMIN_USER_EMAIL") or f"{_ADMIN_LOGIN}{'@'}{_ADMIN_DOMAIN}"
ADMIN_PASSWORD = os.getenv("ADMIN_USER_PASSWORD", "admin12345")
ADMIN_NAME = ("Администратор", "BudgetTracker")


async def seed_admin(keep_password: bool = False) -> None:
    async with async_session_maker() as session:
        user = (await session.execute(select(UserModel).where(UserModel.email == ADMIN_EMAIL))).scalar_one_or_none()

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
                # The column is unique and NOT NULL: 0 is taken by the demo user,
                # and a negative id can never collide with a real Telegram one
                telegram_id=-1,
            )
            session.add(user)
            await session.commit()
            print(f"[admin] superuser created: {ADMIN_EMAIL}")
        else:
            # The email may have been changed — restore the default one
            user.email = ADMIN_EMAIL
            user.is_superuser = True
            user.is_verified = True
            user.is_active = True
            if not keep_password:
                user.password = get_password_hash(ADMIN_PASSWORD)
            await session.commit()
            print(f"[admin] superuser updated: {ADMIN_EMAIL}")

    print("[admin] done")
    print(f"[admin] login: {ADMIN_EMAIL} / " + ("password unchanged" if keep_password else ADMIN_PASSWORD))


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="BudgetTracker administrator with default credentials")
    parser.add_argument(
        "--keep-password",
        action="store_true",
        help="do not reset an existing user's password to the default",
    )
    args = parser.parse_args(argv)
    asyncio.run(seed_admin(keep_password=args.keep_password))


if __name__ == "__main__":
    main()
