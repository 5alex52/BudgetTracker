"""Move subscription charges into the shared «Связь и подписки → Подписки» category.

Earlier every attached subscription created its own top-level expense category
named after the service ("YouTube", "Netflix", ...). New subscriptions share one
subcategory, so this script rewrites the existing ones:

* the subscription's category becomes «Подписки»;
* its auto-charge records (``service_sub_id`` set) move there too;
* the old per-service category is deleted when nothing references it anymore
  (manual records recorded under it keep it alive — nothing is lost).

Idempotent. Without ``--apply`` it only prints the plan. Run in the backend
container from the project root::

    docker compose exec backend python -m scripts.migrate_subscription_categories
    docker compose exec backend python -m scripts.migrate_subscription_categories --apply
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import redis.asyncio as aioredis  # noqa: E402
from sqlalchemy import func  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy import update  # noqa: E402

import src.finance.models  # noqa: F401,E402 — register the mappers
import src.users.models  # noqa: F401,E402
from src.cache import Cache  # noqa: E402
from src.config import settings  # noqa: E402
from src.database import async_session_maker  # noqa: E402
from src.finance.models import CategoryModel  # noqa: E402
from src.finance.models import ServiceSubscriptionModel  # noqa: E402
from src.finance.models import TemplateModel  # noqa: E402
from src.finance.models import TransactionModel  # noqa: E402
from src.finance.schemas import CategoryType  # noqa: E402
from src.finance.service_subs import SUBSCRIPTION_LEAF  # noqa: E402
from src.finance.service_subs import SUBSCRIPTION_ROOT  # noqa: E402
from src.finance.service_subs import ServiceSubService  # noqa: E402
from src.users.models import UserModel  # noqa: E402


async def _connect_cache() -> aioredis.Redis | None:
    """Wire the app cache: the script runs outside the app startup, so it is off by default."""
    client = aioredis.Redis(
        host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, decode_responses=True, socket_connect_timeout=2
    )
    try:
        await client.ping()
    except Exception:  # noqa: BLE001 — no cache is not a reason to fail the migration
        await client.aclose()
        return None
    Cache.configure(client)
    return client


async def _existing_target(session, user_id) -> int | None:
    """The «Подписки» category if the user already has it; creates nothing."""
    leaf = (
        (
            await session.execute(
                select(CategoryModel.id)
                .where(
                    CategoryModel.user_id == user_id,
                    CategoryModel.name == SUBSCRIPTION_LEAF,
                    CategoryModel.type == CategoryType.EXPENSE,
                )
                .limit(1)
            )
        )
        .scalars()
        .first()
    )
    if leaf is not None:
        return leaf
    return (
        (
            await session.execute(
                select(CategoryModel.id)
                .where(
                    CategoryModel.user_id == user_id,
                    CategoryModel.name == SUBSCRIPTION_ROOT,
                    CategoryModel.parent_id.is_(None),
                    CategoryModel.type == CategoryType.EXPENSE,
                )
                .limit(1)
            )
        )
        .scalars()
        .first()
    )


async def _unreferenced(session, category_id: int) -> bool:
    """True when no record, template, subscription or child category uses it."""
    for model in (TransactionModel, TemplateModel, ServiceSubscriptionModel):
        count = await session.scalar(select(func.count()).select_from(model).where(model.category_id == category_id))
        if count:
            return False
    children = await session.scalar(
        select(func.count()).select_from(CategoryModel).where(CategoryModel.parent_id == category_id)
    )
    return not children


async def main(apply: bool) -> None:
    async with async_session_maker() as session:
        users = (await session.execute(select(UserModel))).scalars().all()

    moved = 0
    removed = 0
    for user in users:
        async with async_session_maker() as session:
            subs = (
                (
                    await session.execute(
                        select(ServiceSubscriptionModel).where(
                            ServiceSubscriptionModel.user_id == user.id,
                            ServiceSubscriptionModel.category_id.is_not(None),
                        )
                    )
                )
                .scalars()
                .all()
            )
            if not subs:
                continue
            target = await _existing_target(session, user.id)
            if target is None:
                if apply:
                    target = await ServiceSubService._subscription_category(session, user.id, async_session_maker)
                else:
                    print(f"  {user.email}: would create «{SUBSCRIPTION_ROOT} → {SUBSCRIPTION_LEAF}»")
                    continue
            candidates: set[int] = set()
            for sub in subs:
                if sub.category_id == target:
                    continue
                old = await session.get(CategoryModel, sub.category_id)
                # Only categories this feature made itself: top level, named after the service.
                if old is not None and old.parent_id is None and old.name == sub.name:
                    candidates.add(old.id)
                print(f"  {user.email}: «{sub.name}» {old.name if old else sub.category_id} -> «{SUBSCRIPTION_LEAF}»")
                if apply:
                    await session.execute(
                        update(TransactionModel)
                        .where(TransactionModel.service_sub_id == sub.id)
                        .values(category_id=target)
                    )
                    await session.execute(
                        update(ServiceSubscriptionModel)
                        .where(ServiceSubscriptionModel.id == sub.id)
                        .values(category_id=target)
                    )
                moved += 1
            if not apply:
                continue
            await session.flush()
            for category_id in candidates:
                if await _unreferenced(session, category_id):
                    await session.delete(await session.get(CategoryModel, category_id))
                    removed += 1
                else:
                    print(f"  kept category {category_id}: still used by other records")
            await session.commit()

    if apply:
        client = await _connect_cache()
        await Cache.delete_scope("categories")
        await Cache.delete_scope("analytics")
        if client is not None:
            await client.aclose()
    print(f"Done ({'applied' if apply else 'dry run'}): {moved} subscriptions, {removed} empty categories removed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="write changes (default: dry run)")
    asyncio.run(main(parser.parse_args().apply))
