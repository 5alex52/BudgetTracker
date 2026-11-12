"""Telegram Mini App initData signature validation.

Telegram passes the WebApp launch data as an initData string (query-string)
with a hash signature. The signature is verified with HMAC-SHA256 per the
scheme from the documentation:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

import hashlib
import hmac
import json
import time
from typing import Optional
from urllib.parse import parse_qsl

from src.config import settings

# Reject initData older than 24 hours: protects against replay of a stolen string
MAX_AGE_SECONDS = 24 * 60 * 60


def validate_init_data(init_data: str, bot_token: Optional[str] = None) -> dict:
    """Validate the initData signature and freshness; return the parsed fields.

    Raises ValueError on an invalid signature, missing token, or stale data.
    """
    token = bot_token if bot_token is not None else settings.TELEGRAM_BOT_TOKEN
    if not token:
        raise ValueError("Telegram bot token is not configured")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise ValueError("initData has no hash")

    data_check_string = "\n".join(f"{key}={pairs[key]}" for key in sorted(pairs))
    secret_key = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    computed = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed, received_hash):
        raise ValueError("initData signature mismatch")

    auth_date = pairs.get("auth_date")
    if auth_date is None:
        raise ValueError("initData has no auth_date")
    try:
        auth_ts = int(auth_date)
    except ValueError:
        raise ValueError("initData auth_date is not a number")
    now = time.time()
    # Allow a small clock skew, but reject data "from the future" outright.
    if auth_ts > now + 300:
        raise ValueError("initData auth_date is in the future")
    if now - auth_ts > MAX_AGE_SECONDS:
        raise ValueError("initData is too old")

    return pairs


def telegram_user_id(init_data: str, bot_token: Optional[str] = None) -> int:
    """Extract the user's telegram id from validated initData."""
    pairs = validate_init_data(init_data, bot_token)
    user_raw = pairs.get("user")
    if not user_raw:
        raise ValueError("initData has no user")
    try:
        return int(json.loads(user_raw)["id"])
    except (ValueError, KeyError, TypeError):
        raise ValueError("initData user is malformed")
