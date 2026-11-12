"""Telegram Mini App auth: initData signature validation and /auth/telegram login."""

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from httpx import AsyncClient
from src.config import settings
from src.users.service import UserService
from src.users.telegram_auth import telegram_user_id
from src.users.telegram_auth import validate_init_data

TEST_TOKEN = "123456:TEST-telegram-bot-token"

BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
)


def make_init_data(token: str, telegram_id: int, auth_date: int | None = None) -> str:
    """Builds a correctly signed initData query-string for the given Telegram user."""
    pairs = {
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "AAH-test-query",
        "user": json.dumps({"id": telegram_id, "first_name": "Test", "username": "testuser"}),
    }
    data_check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode({**pairs, "hash": signature})


# --- pure signature validation ---


def test_valid_init_data_returns_user_id():
    init_data = make_init_data(TEST_TOKEN, 424242)
    assert telegram_user_id(init_data, TEST_TOKEN) == 424242
    assert validate_init_data(init_data, TEST_TOKEN)["query_id"] == "AAH-test-query"


def test_tampered_signature_rejected():
    init_data = make_init_data(TEST_TOKEN, 424242)
    tampered = init_data.replace("Test", "Evil")
    with pytest.raises(ValueError):
        telegram_user_id(tampered, TEST_TOKEN)


def test_wrong_token_rejected():
    init_data = make_init_data(TEST_TOKEN, 424242)
    with pytest.raises(ValueError):
        telegram_user_id(init_data, "999:OTHER-token")


def test_missing_hash_rejected():
    with pytest.raises(ValueError):
        validate_init_data("auth_date=123&user=%7B%7D", TEST_TOKEN)


def test_expired_init_data_rejected():
    old = int(time.time()) - 25 * 60 * 60
    init_data = make_init_data(TEST_TOKEN, 424242, auth_date=old)
    with pytest.raises(ValueError):
        telegram_user_id(init_data, TEST_TOKEN)


def test_future_auth_date_rejected():
    init_data = make_init_data(TEST_TOKEN, 424242, auth_date=int(time.time()) + 3600)
    with pytest.raises(ValueError):
        telegram_user_id(init_data, TEST_TOKEN)


def test_missing_user_rejected():
    pairs = {"auth_date": str(int(time.time())), "query_id": "q"}
    data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs))
    secret = hmac.new(b"WebAppData", TEST_TOKEN.encode(), hashlib.sha256).digest()
    sig = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()
    with pytest.raises(ValueError):
        telegram_user_id(urlencode({**pairs, "hash": sig}), TEST_TOKEN)


def test_no_token_configured_rejected(monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "")
    with pytest.raises(ValueError):
        validate_init_data(make_init_data(TEST_TOKEN, 1))


# --- endpoint ---


@pytest.mark.asyncio
async def test_telegram_login_requires_valid_init_data(async_client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", TEST_TOKEN)
    response = await async_client.post(
        "/api/auth/telegram",
        json={"init_data": "auth_date=1&hash=deadbeef"},
        headers={"User-Agent": BROWSER_UA},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_telegram_login_unlinked_account(async_client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", TEST_TOKEN)
    response = await async_client.post(
        "/api/auth/telegram",
        json={"init_data": make_init_data(TEST_TOKEN, 999_999_999)},
        headers={"User-Agent": BROWSER_UA},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_telegram_login_linked_account(verified_user_client, session_maker, monkeypatch):
    async_client, user_id, _ = verified_user_client
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", TEST_TOKEN)

    user = await UserService.get_profile(user_id, session_maker)
    init_data = make_init_data(TEST_TOKEN, user.telegram_id)

    # Drop existing session cookies so login must come from initData alone.
    async_client.cookies.clear()
    response = await async_client.post(
        "/api/auth/telegram", json={"init_data": init_data}, headers={"User-Agent": BROWSER_UA}
    )
    assert response.status_code == 200
    assert "access_token" not in response.json()
    # Secure cookies are not sent over http://test — put the token into the jar manually, as in conftest.
    async_client.cookies["access_token"] = response.cookies["access_token"]

    me = await async_client.get("/api/users/me")
    assert me.status_code == 200
    assert me.json()["id"] == str(user_id)
