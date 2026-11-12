"""Subscription charge reminders: Telegram + Web Push.

Runs in the background next to the auto-billing loop. Two jobs on a 30-second
tick: poll the Telegram bot for /start <link-code> messages (chat linking) and,
every 15 minutes, send charge reminders for service subscriptions whose due
date is `user.reminder_days_before` days ahead at 12:00 in the user's timezone.
Each (subscription, due_date) pair is reminded at most once — the
service_sub_reminders table is the dedup log.
"""

import asyncio
import json
import logging
from datetime import datetime
from datetime import time
from datetime import timedelta
from typing import Optional
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from .utils import send_notification

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30
REMINDER_INTERVAL_SECONDS = 15 * 60
REMINDER_TIME = time(12, 0)

_REMIND_TEXT = {
    "ru": "💸 Подписка «{name}»: {price} {currency} — списание {when}.",
    "en": '💸 Subscription "{name}": {price} {currency} — charged {when}.',
}
_WHEN_TEXT = {
    "ru": {0: "сегодня", 1: "завтра", 2: "через 2 дня"},
    "en": {0: "today", 1: "tomorrow", 2: "in 2 days"},
}
_LINK_CONFIRM = {
    "ru": "Готово! Уведомления о списаниях по подпискам будут приходить сюда.",
    "en": "Done! Subscription charge reminders will arrive here.",
}


def should_remind(now_user: datetime, due_local: datetime, lead_days: int) -> bool:
    """Pure decision: is it time to remind about the charge happening on due_local?

    The trigger fires at 12:00 of (due date − lead days) in the user's timezone.
    """
    remind_at = datetime.combine(due_local.date() - timedelta(days=lead_days), REMINDER_TIME)
    return now_user.replace(tzinfo=None) >= remind_at


def reminder_message(name: str, price, currency: str, lead_days: int, locale: Optional[str]) -> str:
    lang = "en" if (locale or "").startswith("en") else "ru"
    when = _WHEN_TEXT[lang].get(lead_days, _WHEN_TEXT[lang][1])
    return _REMIND_TEXT[lang].format(name=name, price=price, currency=currency, when=when)


def _user_now(user) -> datetime:
    """Wall-clock time of the user. Container time is UTC, so it is converted explicitly."""
    try:
        return datetime.now(ZoneInfo(user.timezone or "Europe/Minsk"))
    except Exception:  # noqa: BLE001 — bad tz string must not break the loop
        return datetime.now(ZoneInfo("Europe/Minsk"))


async def run_due_reminders(session_maker: async_sessionmaker) -> int:
    """Sends reminders for subscriptions whose charge date entered the reminder window."""
    from src.config import settings
    from src.finance.models import ServiceSubReminderModel
    from src.finance.models import ServiceSubscriptionModel
    from src.users.models import PushSubscriptionModel
    from src.users.models import UserModel

    sent = 0
    async with session_maker() as session:  # type: AsyncSession
        subs = (await session.execute(select(ServiceSubscriptionModel, UserModel).join(UserModel))).all()
        push_rows = (await session.execute(select(PushSubscriptionModel))).scalars().all()

        for service_sub, user in subs:
            if service_sub.next_payment_date is None:
                continue
            lead = min(max(user.reminder_days_before if user.reminder_days_before is not None else 1, 0), 2)
            now_user = _user_now(user)
            # next_payment_date is stored naive and is treated as the user's wall time
            due_local = service_sub.next_payment_date.replace(tzinfo=now_user.tzinfo)
            if not should_remind(now_user, due_local, lead):
                continue
            due_date = due_local.date()
            already = await session.scalar(
                select(ServiceSubReminderModel.id).where(
                    ServiceSubReminderModel.service_sub_id == service_sub.id,
                    ServiceSubReminderModel.due_date == due_date,
                )
            )
            if already is not None:
                continue

            message = reminder_message(
                service_sub.name, float(service_sub.price), service_sub.currency_id, lead, user.locale
            )
            deliverable = False
            # Telegram: needs both a linked chat and a configured bot
            if user.telegram_id and settings.TELEGRAM_BOT_TOKEN:
                try:
                    await send_notification("telegram", str(user.telegram_id), None, message)
                    deliverable = True
                except Exception as caught:  # noqa: BLE001
                    logger.warning("Telegram reminder failed for user %s: %s", user.id, caught)
            # Web Push: needs VAPID keys and at least one browser subscription
            if settings.VAPID_PUBLIC_KEY and settings.VAPID_PRIVATE_KEY:
                for sub in (p for p in push_rows if p.user_id == user.id):
                    try:
                        from pywebpush import webpush

                        webpush(
                            subscription_info={
                                "endpoint": sub.endpoint,
                                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                            },
                            data=json.dumps({"title": "BudgetTracker", "body": message, "url": "/"}),
                            vapid_private_key=settings.VAPID_PRIVATE_KEY,
                            vapid_claims={"sub": settings.VAPID_SUBJECT},
                        )
                        deliverable = True
                    except Exception as caught:  # noqa: BLE001
                        if getattr(getattr(caught, "response", None), "status_code", None) in (404, 410):
                            await session.execute(
                                sa_delete(PushSubscriptionModel).where(PushSubscriptionModel.id == sub.id)
                            )
                            await session.commit()
                        logger.warning("Web push reminder failed for user %s: %s", user.id, caught)
            if not deliverable:
                continue  # nobody to deliver to: keep the reminder pending

            session.add(ServiceSubReminderModel(service_sub_id=service_sub.id, due_date=due_date))
            await session.commit()
            sent += 1
    return sent


async def poll_telegram_linking(session_maker: async_sessionmaker, next_offset: int) -> int:
    """Links Telegram chats: /start <code> → user's telegram_id = chat id.

    Returns the offset for the next poll (update_id + 1 of the last seen update).
    """
    from src.config import settings
    from src.users.models import UserModel

    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return next_offset
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"https://api.telegram.org/bot{token}/getUpdates",
                params={"offset": next_offset, "timeout": 0, "allowed_updates": ["message"]},
            )
            updates = (response.json() or {}).get("result") or []
    except Exception as caught:  # noqa: BLE001 — bot API is a best-effort dependency
        logger.warning("Telegram getUpdates failed: %s", caught)
        return next_offset

    for update in updates:
        next_offset = max(next_offset, update["update_id"] + 1)
        message = update.get("message") or {}
        text = (message.get("text") or "").strip()
        if not text.startswith("/start"):
            continue
        code = text[len("/start") :].strip()
        if not code:
            continue
        async with session_maker() as session:  # type: AsyncSession
            user = (
                await session.execute(select(UserModel).where(UserModel.telegram_link_code == code))
            ).scalar_one_or_none()
            if user is None:
                continue
            user.telegram_id = (message.get("chat") or {}).get("id")
            user.telegram_link_code = None
            await session.commit()
            if user.telegram_id:
                lang = "en" if (user.locale or "").startswith("en") else "ru"
                try:
                    await send_notification("telegram", str(user.telegram_id), None, _LINK_CONFIRM[lang])
                except Exception as caught:  # noqa: BLE001 — the link is already saved; confirmation is best-effort
                    logger.warning("Telegram link confirmation to %s failed: %s", user.telegram_id, caught)
    return next_offset


async def notification_loop(session_maker: async_sessionmaker) -> None:
    """Background loop: chat linking every tick, reminders every 15 minutes."""
    next_offset = 0
    ticks = 0
    while True:
        try:
            next_offset = await poll_telegram_linking(session_maker, next_offset)
            ticks += 1
            if ticks % (REMINDER_INTERVAL_SECONDS // POLL_INTERVAL_SECONDS) == 0:
                sent = await run_due_reminders(session_maker)
                if sent:
                    logger.info("Subscription reminders sent: %s", sent)
        except Exception as caught:  # noqa: BLE001 — the loop must survive any error
            logger.exception("Notification loop iteration failed: %s", caught)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
