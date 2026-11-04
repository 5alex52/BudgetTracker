"""Тесты админ-панели: доступ, список пользователей, выдача и отзыв подписки."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func
from sqlalchemy import select
from src.billing.models import PaymentModel
from src.billing.models import PlanModel
from src.billing.models import PlanPeriod
from src.billing.models import PlanSubscriptionModel
from src.users.models import UserModel


async def _seed_plans(session_maker) -> None:
    async with session_maker() as session:
        for code, name, price, period in (
            ("free", "Бесплатный", 0.0, PlanPeriod.NONE),
            ("monthly", "Месячный", 1.99, PlanPeriod.MONTH),
            ("yearly", "Годовой", 19.99, PlanPeriod.YEAR),
        ):
            session.add(
                PlanModel(
                    code=code,
                    name=name,
                    price=price,
                    currency="USD",
                    period=period,
                    features=[],
                    sort_order=0,
                )
            )
        await session.commit()


@pytest_asyncio.fixture
async def superuser_client(verified_user_client, session_maker):
    """Поднимает обычного пользователя до суперпользователя."""
    client, user_id, _ = verified_user_client
    async with session_maker() as session:
        user = await session.get(UserModel, user_id)
        user.is_superuser = True
        await session.commit()
    return client, user_id


@pytest.mark.asyncio
async def test_admin_endpoints_require_superuser(verified_user_client):
    async_client, _, _ = verified_user_client

    response = await async_client.get("/api/admin/stats")

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_lists_and_finds_users(superuser_client, other_user):
    async_client, _ = superuser_client

    response = await async_client.get("/api/admin/users", params={"search": other_user.email})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["email"] == other_user.email
    assert payload["items"][0]["is_premium"] is False


@pytest.mark.asyncio
async def test_admin_grants_and_revokes_subscription(superuser_client, other_user, session_maker):
    async_client, _ = superuser_client
    await _seed_plans(session_maker)

    granted = await async_client.post(
        f"/api/admin/users/{other_user.id}/subscription",
        json={"plan_code": "monthly"},
    )

    assert granted.status_code == 200
    row = granted.json()
    assert row["is_premium"] is True
    assert row["plan_code"] == "monthly"
    assert row["current_period_end"] is not None

    async with session_maker() as session:
        subscription = (
            (await session.execute(select(PlanSubscriptionModel).where(PlanSubscriptionModel.user_id == other_user.id)))
            .scalars()
            .one()
        )
        payments = await session.scalar(select(func.count()).select_from(PaymentModel))

    assert subscription.provider == "admin"
    assert payments == 0

    revoked = await async_client.delete(f"/api/admin/users/{other_user.id}/subscription")

    assert revoked.status_code == 200
    assert revoked.json()["is_premium"] is False
    assert revoked.json()["subscription_status"] == "canceled"

    again = await async_client.delete(f"/api/admin/users/{other_user.id}/subscription")
    assert again.status_code == 404


@pytest.mark.asyncio
async def test_admin_cannot_grant_free_plan(superuser_client, other_user, session_maker):
    async_client, _ = superuser_client
    await _seed_plans(session_maker)

    response = await async_client.post(
        f"/api/admin/users/{other_user.id}/subscription",
        json={"plan_code": "free"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_cannot_block_superuser(superuser_client):
    async_client, admin_id = superuser_client

    response = await async_client.patch(f"/api/admin/users/{admin_id}", json={"is_active": False})

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_stats_include_subscriptions_and_revenue(superuser_client, other_user, session_maker):
    async_client, _ = superuser_client
    await _seed_plans(session_maker)
    await async_client.post(f"/api/admin/users/{other_user.id}/subscription", json={"plan_code": "yearly"})

    response = await async_client.get("/api/admin/stats")

    assert response.status_code == 200
    stats = response.json()
    assert stats["users_total"] >= 2
    assert stats["premium_total"] == 1
    assert stats["free_total"] == stats["users_total"] - 1
    assert stats["revenue_30d"] == 0
    by_code = {plan["code"]: plan["count"] for plan in stats["plans"]}
    assert by_code["yearly"] == 1
    assert by_code["free"] == stats["free_total"]


@pytest.mark.asyncio
async def test_admin_updates_user_fields(superuser_client, other_user):
    async_client, _ = superuser_client

    response = await async_client.patch(
        f"/api/admin/users/{other_user.id}",
        json={"firstname": "Иван", "lastname": "Тестов", "email": other_user.email},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["fullname"] == "Иван Тестов"


@pytest.mark.asyncio
async def test_admin_subscription_timeline(superuser_client, other_user, session_maker):
    async_client, _ = superuser_client
    await _seed_plans(session_maker)
    await async_client.post(f"/api/admin/users/{other_user.id}/subscription", json={"plan_code": "monthly"})

    response = await async_client.get("/api/admin/stats/subscriptions", params={"days": 7})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["points"]) == 7
    last = payload["points"][-1]
    assert last["premium"] >= 1
