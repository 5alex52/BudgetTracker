"""Profile tests: reading, editing, password, export, and account deletion."""

import pytest
from httpx import AsyncClient

#: Login requires a parseable User-Agent — the same one the browser sends in conftest
BROWSER_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
}


@pytest.mark.asyncio
async def test_profile_requires_authentication(async_client: AsyncClient):
    response = await async_client.get("/api/users/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_returns_current_user(verified_user_client, user_info):
    async_client, user_id, _ = verified_user_client

    response = await async_client.get("/api/users/me")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(user_id)
    assert payload["email"] == user_info.email
    assert payload["locale"] == "ru"
    assert payload["theme"] == "system"
    assert payload["base_currency"] == "BYN"


@pytest.mark.asyncio
async def test_update_me_changes_preferences(verified_user_client):
    async_client, _, _ = verified_user_client

    response = await async_client.patch(
        "/api/users/me",
        json={
            "firstname": "Иван",
            "locale": "en",
            "theme": "dark",
            "base_currency": "USD",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["firstname"] == "Иван"
    assert payload["locale"] == "en"
    assert payload["theme"] == "dark"
    assert payload["base_currency"] == "USD"


@pytest.mark.asyncio
async def test_update_me_cannot_grant_superuser(verified_user_client):
    async_client, _, _ = verified_user_client

    response = await async_client.patch("/api/users/me", json={"is_superuser": True, "is_active": False})

    assert response.status_code == 200
    assert response.json()["is_superuser"] is False
    assert response.json()["is_active"] is True


@pytest.mark.asyncio
async def test_update_me_validates_theme(verified_user_client):
    async_client, _, _ = verified_user_client

    response = await async_client.patch("/api/users/me", json={"theme": "neon"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_update_me_rejects_invalid_email(verified_user_client):
    async_client, _, _ = verified_user_client

    response = await async_client.patch("/api/users/me", json={"email": "not-an-email"})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_change_password_requires_current_password(verified_user_client):
    async_client, _, _ = verified_user_client

    response = await async_client.post(
        "/api/users/me/password",
        json={"old_password": "wrong-pass", "new_password": "new-secret-123"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_change_password_updates_login(verified_user_client, user_info):
    async_client, _, _ = verified_user_client

    response = await async_client.post(
        "/api/users/me/password",
        json={"old_password": user_info.password, "new_password": "new-secret-123"},
    )
    assert response.status_code == 204

    login = await async_client.post(
        "/api/auth/login",
        data={
            "username": user_info.email,
            "password": "new-secret-123",
            "grant_type": "password",
        },
        headers=BROWSER_HEADERS,
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_export_contains_financial_data(verified_user_client, currencies):
    async_client, _, _ = verified_user_client

    await async_client.post(
        "/api/finance/accounts/",
        json={"name": "Cash", "type": "cash", "currency_id": "USD", "balance": 10.0},
    )
    await async_client.post("/api/finance/categories/", json={"name": "Food", "type": "expense"})

    response = await async_client.get("/api/users/me/export")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["accounts"]) == 1
    # Default categories are added alongside the created one.
    assert "Food" in [category["name"] for category in payload["categories"]]
    assert payload["accounts"][0]["name"] == "Cash"
    assert payload["user"]["email"]


@pytest.mark.asyncio
async def test_delete_me_requires_password(verified_user_client):
    async_client, _, _ = verified_user_client

    response = await async_client.request("DELETE", "/api/users/me", json={"password": "wrong"})

    assert response.status_code == 400
    assert (await async_client.get("/api/users/me")).status_code == 200


@pytest.mark.asyncio
async def test_delete_me_removes_user_and_data(verified_user_client, user_info, currencies):
    async_client, _, _ = verified_user_client

    await async_client.post(
        "/api/finance/accounts/",
        json={"name": "Cash", "type": "cash", "currency_id": "USD", "balance": 10.0},
    )

    response = await async_client.request("DELETE", "/api/users/me", json={"password": user_info.password})
    assert response.status_code == 204

    # The session is no longer valid: the user is gone
    assert (await async_client.get("/api/users/me")).status_code in {401, 404}

    login = await async_client.post(
        "/api/auth/login",
        data={
            "username": user_info.email,
            "password": user_info.password,
            "grant_type": "password",
        },
        headers=BROWSER_HEADERS,
    )
    assert login.status_code in {401, 403, 404}
