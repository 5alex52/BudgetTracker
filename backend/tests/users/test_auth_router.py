import pytest
from httpx import AsyncClient
from src.users.schemas import UserCreate


@pytest.mark.asyncio
async def test_logout(verified_user_client):
    async_client, _, refresh_token = verified_user_client

    # Test logout
    response = await async_client.post("/api/auth/logout", data={"refresh_token": refresh_token})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_refresh_token(verified_user_client):
    async_client, _, _ = verified_user_client
    response = await async_client.post("/api/auth/refresh")

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()


@pytest.mark.asyncio
async def test_get_sessions(verified_user_client):
    async_client, _, refresh_token = verified_user_client
    response = await async_client.get("/api/auth/sessions")

    assert response.status_code == 200
    assert response.json()[0]["refresh_token"] == refresh_token


@pytest.mark.asyncio
async def test_abort_all_sessions(verified_user_client):
    async_client, _, _ = verified_user_client
    # Test get sessions
    response = await async_client.get("/api/auth/sessions")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_send_verification_email(async_client: AsyncClient, user_info: UserCreate):
    # First register a user
    await async_client.post("/api/auth/register", json=user_info.model_dump())
    response = await async_client.post("/api/auth/send-verification-email", params={"user_email": user_info.email})
    print(response.json())
    assert response.status_code == 200
    assert response.json()["message"] == "Verification email sent"
