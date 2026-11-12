"""Seed default categories for users who have none.

Registration creates the set right away, but accounts created before this
feature (e.g. the administrator) were left with an empty list. The script is
idempotent: it does not touch users who already have categories.

Run inside the backend container (from the project root)::

    docker compose exec backend python -m scripts.backfill_default_categories
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402

import src.billing.models  # noqa: F401,E402 — register the mappers
import src.finance.models  # noqa: F401,E402
import src.users.models  # noqa: F401,E402
from src.database import async_session_maker  # noqa: E402
from src.finance.models import CategoryModel  # noqa: E402
from src.finance.service import CategoryService  # noqa: E402
from src.users.models import UserModel  # noqa: E402


async def main() -> None:
    async with async_session_maker() as session:
        users = (await session.execute(select(UserModel))).scalars().all()

    total = 0
    for user in users:
        async with async_session_maker() as session:
            has_any = (
                await session.execute(select(CategoryModel.id).where(CategoryModel.user_id == user.id).limit(1))
            ).first()
        if has_any:
            continue
        await CategoryService.create_defaults_for_user(user.id)
        print(f"+ {user.email}")
        total += 1

    print(f"Done: categories added for {total} of {len(users)} users")


if __name__ == "__main__":
    asyncio.run(main())
