"""Subscription charge reminders: timing logic, message text, profile and push endpoints."""

from datetime import datetime
from datetime import timedelta

import pytest
from httpx import AsyncClient

from src.notifications.reminders import reminder_message
from src.notifications.reminders import should_remind

# --- pure timing logic -----------------------------------------------------


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


# --- message text ----------------------------------------------------------


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


# --- profile ---------------------------------------------------------------


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


# --- push subscriptions ----------------------------------------------------


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

    # subscribing again with the same endpoint — upsert, no duplicates
    response = await async_client.post("/api/users/me/push", json=PUSH_PAYLOAD)
    assert response.status_code == 204

    response = await async_client.request("DELETE", "/api/users/me/push", json=PUSH_PAYLOAD)
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_push_requires_authentication(async_client: AsyncClient):
    assert (await async_client.post("/api/users/me/push", json=PUSH_PAYLOAD)).status_code == 401


@pytest.mark.asyncio
async def test_push_subscribe_rejects_http_endpoint(verified_user_client):
    """http endpoints would let the server be aimed at internal hosts (SSRF)."""
    async_client, _, _ = verified_user_client

    payload = {**PUSH_PAYLOAD, "endpoint": "http://169.254.169.254/latest/meta-data/"}
    response = await async_client.post("/api/users/me/push", json=payload)

    assert response.status_code == 422


# --- Telegram linking ------------------------------------------------------


@pytest.mark.asyncio
async def test_telegram_link_returns_code(verified_user_client):
    async_client, _, _ = verified_user_client

    response = await async_client.get("/api/users/me/telegram/link")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["code"]) == 16
    # a repeated request does not change the code
    again = await async_client.get("/api/users/me/telegram/link")
    assert again.json()["code"] == payload["code"]


@pytest.mark.asyncio
async def test_telegram_unlink(verified_user_client):
    async_client, _, _ = verified_user_client

    assert (await async_client.delete("/api/users/me/telegram")).status_code == 204


# --- lead=0 after auto-billing ----------------------------------------------


@pytest.mark.asyncio
async def test_lead_zero_reminds_after_billing_advanced_the_date(
    session_maker, user, account, expense_category, currencies, monkeypatch
):
    """collect_due bills at 00:00 and advances next_payment_date a period ahead;
    the "due today" reminder at 12:00 must still fire from today's charge."""
    from zoneinfo import ZoneInfo

    from sqlalchemy import select
    from src.config import settings
    from src.finance.models import ServiceSubReminderModel
    from src.finance.models import ServiceSubscriptionModel
    from src.finance.models import TransactionModel
    from src.finance.schemas import TransactionType
    from src.notifications import reminders
    from src.users.models import UserModel

    noon = datetime(2026, 11, 12, 12, 0, tzinfo=ZoneInfo("Europe/Minsk"))
    monkeypatch.setattr(reminders, "_user_now", lambda _user: noon)
    monkeypatch.setattr(settings, "TELEGRAM_BOT_TOKEN", "test-token")
    delivered = []

    async def fake_send(channel, target, title, message):
        delivered.append(message)

    monkeypatch.setattr(reminders, "send_notification", fake_send)

    async with session_maker() as session:
        db_user = await session.get(UserModel, user.id)
        db_user.reminder_days_before = 0
        db_user.telegram_id = 123456789
        charged = ServiceSubscriptionModel(
            user_id=user.id,
            name="Netflix",
            price=9.99,
            currency_id="USD",
            started_at=datetime(2026, 10, 12),
            account_id=account.id,
            category_id=expense_category.id,
            # already billed today at 00:00 — the stored date is a month ahead
            next_payment_date=datetime(2026, 12, 12),
        )
        future = ServiceSubscriptionModel(
            user_id=user.id,
            name="Spotify",
            price=4.99,
            currency_id="USD",
            started_at=datetime(2026, 10, 20),
            next_payment_date=datetime(2026, 12, 20),
        )
        session.add_all([charged, future])
        await session.flush()
        session.add(
            TransactionModel(
                account_id=account.id,
                category_id=expense_category.id,
                amount=9.99,
                currency_id="USD",
                type=TransactionType.EXPENSE,
                date=datetime(2026, 11, 12, 0, 0),
                service_sub_id=charged.id,
                is_subscription=True,
            )
        )
        await session.commit()
        charged_id = charged.id

    assert await reminders.run_due_reminders(session_maker) == 1
    assert len(delivered) == 1
    assert "Netflix" in delivered[0] and "сегодня" in delivered[0]

    async with session_maker() as session:
        dedup = (
            await session.execute(
                select(ServiceSubReminderModel).where(ServiceSubReminderModel.service_sub_id == charged_id)
            )
        ).scalar_one()
        assert dedup.due_date == datetime(2026, 11, 12).date()

    # second pass: one reminder per due date, the future sub stays silent
    assert await reminders.run_due_reminders(session_maker) == 0
