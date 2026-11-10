"""Admin panel tests: access, user list and user management."""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from src.users.models import UserModel


@pytest_asyncio.fixture
async def superuser_client(verified_user_client, session_maker):
    """Promotes a regular user to superuser."""
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

    response = await async_client.get(
        "/api/admin/users", params={"search": other_user.email}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["email"] == other_user.email


@pytest.mark.asyncio
async def test_admin_cannot_block_superuser(superuser_client):
    async_client, admin_id = superuser_client

    response = await async_client.patch(
        f"/api/admin/users/{admin_id}", json={"is_active": False}
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_stats(superuser_client, other_user):
    async_client, _ = superuser_client

    response = await async_client.get("/api/admin/stats")

    assert response.status_code == 200
    stats = response.json()
    assert stats["users_total"] >= 2
    assert stats["users_new_30d"] >= 2


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
