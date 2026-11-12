"""Subscription charge reminders: timing logic, message text, profile and push endpoints."""

from datetime import datetime
from datetime import timedelta

import pytest
from httpx import AsyncClient

from src.notifications.reminders import reminder_message
from src.notifications.reminders import should_remind

# --- чистая логика времени -----------------------------------------------


def _at(day_offset: int, hour: int, minute: int = 0) -> datetime:
    base = datetime(2026, 11, 12)
    return base.replace(hour=hour, minute=minute) + timedelta(days=day_offset)


def test_remind_same_day_at_noon():
    due = _at(0, 0)
    assert not should_remind(_at(0, 11, 59), due, lead_days=0)
    assert should_remind(_at(0, 12, 0), due, lead_days=0)


def test_remind_one_day_before():
    due = _at(1, 0)
    assert not should_remind(_at(0, 11, 59), due, lead_days=1)
    assert should_remind(_at(0, 12, 0), due, lead_days=1)


def test_remind_two_days_before():
    due = _at(2, 0)
    assert not should_remind(_at(0, 11, 59), due, lead_days=2)
    assert should_remind(_at(0, 12, 0), due, lead_days=2)


def test_overdue_still_reminds_once():
    due = _at(-3, 0)
    assert should_remind(_at(0, 12, 0), due, lead_days=1)


# --- текст сообщения -------------------------------------------------------


def test_message_ru_lead_variants():
    assert "сегодня" in reminder_message("Netflix", 9.99, "USD", 0, "ru")
    assert "завтра" in reminder_message("Netflix", 9.99, "USD", 1, "ru")
    assert "через 2 дня" in reminder_message("Netflix", 9.99, "USD", 2, "ru")
    assert "Netflix" in reminder_message("Netflix", 9.99, "USD", 1, "ru")
    assert "9.99" in reminder_message("Netflix", 9.99, "USD", 1, "ru")


def test_message_en_lead_variants():
    assert "today" in reminder_message("Netflix", 9.99, "USD", 0, "en")
    assert "tomorrow" in reminder_message("Netflix", 9.99, "USD", 1, "en")
    assert "in 2 days" in reminder_message("Netflix", 9.99, "USD", 2, "en")


def test_message_unknown_locale_falls_back_to_ru():
    assert "завтра" in reminder_message("Netflix", 9.99, "USD", 1, "de")


# --- профиль ----------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_me_sets_reminder_days_before(verified_user_client):
    async_client, _, _ = verified_user_client

    response = await async_client.patch("/api/users/me", json={"reminder_days_before": 2})

    assert response.status_code == 200
    assert response.json()["reminder_days_before"] == 2


@pytest.mark.asyncio
async def test_update_me_rejects_out_of_range_lead(verified_user_client):
    async_client, _, _ = verified_user_client

    assert (await async_client.patch("/api/users/me", json={"reminder_days_before": 3})).status_code == 422
    assert (await async_client.patch("/api/users/me", json={"reminder_days_before": -1})).status_code == 422


# --- push-подписки ----------------------------------------------------------


PUSH_PAYLOAD = {
    "endpoint": "https://push.example/send/abc",
    "keys": {"p256dh": "BJtf4Kbg3O4MAcfFpex8Kad", "auth": "secret-auth"},
}


@pytest.mark.asyncio
async def test_push_public_key_endpoint(verified_user_client):
    async_client, _, _ = verified_user_client

    response = await async_client.get("/api/users/me/push/public-key")

    assert response.status_code == 200
    assert "public_key" in response.json()


@pytest.mark.asyncio
async def test_push_subscribe_and_unsubscribe(verified_user_client):
    async_client, _, _ = verified_user_client

    response = await async_client.post("/api/users/me/push", json=PUSH_PAYLOAD)
    assert response.status_code == 204

    # повторная подписка тем же endpoint — upsert, без дублей
    response = await async_client.post("/api/users/me/push", json=PUSH_PAYLOAD)
    assert response.status_code == 204

    response = await async_client.request("DELETE", "/api/users/me/push", json=PUSH_PAYLOAD)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_push_requires_authentication(async_client: AsyncClient):
    assert (await async_client.post("/api/users/me/push", json=PUSH_PAYLOAD)).status_code == 401


# --- привязка Telegram -------------------------------------------------------


@pytest.mark.asyncio
async def test_telegram_link_returns_code(verified_user_client):
    async_client, _, _ = verified_user_client

    response = await async_client.get("/api/users/me/telegram/link")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["code"]) == 8
    # повторный запрос не меняет код
    again = await async_client.get("/api/users/me/telegram/link")
    assert again.json()["code"] == payload["code"]


@pytest.mark.asyncio
async def test_telegram_unlink(verified_user_client):
    async_client, _, _ = verified_user_client

    assert (await async_client.delete("/api/users/me/telegram")).status_code == 204
