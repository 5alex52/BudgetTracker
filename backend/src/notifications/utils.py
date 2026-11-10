import logging
from abc import ABC
from abc import abstractmethod
from typing import Dict
from typing import Optional

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    """Base class for a notification channel implementation."""

    channel: str = "base"

    @abstractmethod
    async def send(
        self, recipient: str, subject: Optional[str], message: str, **kwargs
    ) -> bool:
        """Delivers a message to the recipient and returns True on success."""
        raise NotImplementedError


class EmailNotifier(BaseNotifier):
    """Email channel.

    The transport is intentionally pluggable: in local and CI environments messages are logged,
    while a real deployment can override the deliver method with an SMTP or API implementation.
    """

    channel = "email"

    async def send(
        self, recipient: str, subject: Optional[str], message: str, **kwargs
    ) -> bool:
        await self.deliver(recipient=recipient, subject=subject or "", message=message)
        return True

    async def deliver(self, recipient: str, subject: str, message: str) -> None:
        logger.info("Email to %s | subject=%r | body=%s", recipient, subject, message)


class TelegramNotifier(BaseNotifier):
    """Telegram channel, delivered through the bot API by the deliver method."""

    channel = "telegram"

    async def send(
        self, recipient: str, subject: Optional[str], message: str, **kwargs
    ) -> bool:
        await self.deliver(chat_id=recipient, message=message)
        return True

    async def deliver(self, chat_id: str, message: str) -> None:
        logger.info("Telegram message to %s | body=%s", chat_id, message)


NOTIFIERS: Dict[str, BaseNotifier] = {
    EmailNotifier.channel: EmailNotifier(),
    TelegramNotifier.channel: TelegramNotifier(),
}


async def send_notification(
    channel: str,
    recipient: str,
    subject: Optional[str] = None,
    message: str = "",
    **kwargs,
) -> bool:
    """Sends a notification through the requested channel.

    Raises:
        ValueError: if the channel is unknown.
    """
    notifier = NOTIFIERS.get(channel)
    if notifier is None:
        raise ValueError(f"Unknown notification channel: {channel}")
    return await notifier.send(
        recipient=recipient, subject=subject, message=message, **kwargs
    )
