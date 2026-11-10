"""Cache layer over Redis.

The scaffolding was already in place: the client is created in the application lifespan and in ``src/celery.py``.
This is a thin wrapper used by services to avoid fetching the same aggregate from the database on every page render.

The main rule: **the cache must not break the application**. If Redis is not connected
(local development, a crashed instance), all methods become no-ops and the service
computes data as usual.
"""

import hashlib
import json
import logging
from typing import Any
from typing import Optional

logger = logging.getLogger(__name__)

#: Prefix for all application keys: other projects may share the same Redis instance
PREFIX = "bt"


class Cache:
    """Asynchronous cache with graceful degradation."""

    _client: Any = None

    # ------------------------------------------------------------------ #
    #  Connection
    # ------------------------------------------------------------------ #

    @classmethod
    def configure(cls, client: Any) -> None:
        cls._client = client

    @classmethod
    def reset(cls) -> None:
        cls._client = None

    @classmethod
    def enabled(cls) -> bool:
        return cls._client is not None

    # ------------------------------------------------------------------ #
    #  Keys
    # ------------------------------------------------------------------ #

    @staticmethod
    def make_key(scope: str, **parts: Any) -> str:
        """Deterministic key: ``bt:scope:hash(params)``.

        Parameters are hashed, so long dates and lists do not inflate the key,
        and the order of arguments does not affect cache hits.
        """
        payload = json.dumps(parts, sort_keys=True, default=str, ensure_ascii=False)
        digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:20]
        return f"{PREFIX}:{scope}:{digest}"

    # ------------------------------------------------------------------ #
    #  Read and write
    # ------------------------------------------------------------------ #

    @classmethod
    async def get(cls, key: str) -> Optional[Any]:
        if cls._client is None:
            return None
        try:
            raw = await cls._client.get(key)
        except Exception as caught:  # noqa: BLE001 — cache must not crash a request
            logger.warning("Cache read failed (%s): %s", key, caught)
            return None
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            logger.warning("Cache value is not JSON (%s)", key)
            return None

    @classmethod
    async def set(cls, key: str, value: Any, ttl: int = 60) -> None:
        if cls._client is None:
            return
        try:
            payload = json.dumps(value, default=str, ensure_ascii=False)
            await cls._client.set(key, payload, ex=ttl)
        except Exception as caught:  # noqa: BLE001
            logger.warning("Cache write failed (%s): %s", key, caught)

    @classmethod
    async def delete(cls, *keys: str) -> None:
        if cls._client is None or not keys:
            return
        try:
            await cls._client.delete(*keys)
        except Exception as caught:  # noqa: BLE001
            logger.warning("Cache delete failed: %s", caught)

    @classmethod
    async def delete_scope(cls, scope: str) -> None:
        """Invalidates an entire scope: needed after writes that affect aggregates.

        Uses ``SCAN`` instead of ``KEYS``: the latter blocks Redis on large databases.
        """
        if cls._client is None:
            return
        pattern = f"{PREFIX}:{scope}:*"
        try:
            cursor = 0
            while True:
                cursor, found = await cls._client.scan(
                    cursor=cursor, match=pattern, count=200
                )
                if found:
                    await cls._client.delete(*found)
                if cursor == 0:
                    break
        except Exception as caught:  # noqa: BLE001
            logger.warning("Cache scope reset failed (%s): %s", scope, caught)


async def cached(scope: str, key_parts: dict, ttl: int, factory):
    """Return a value from the cache, or compute and store it.

    ``factory`` is a no-argument coroutine. Computation errors are not cached.
    """
    key = Cache.make_key(scope, **key_parts)
    hit = await Cache.get(key)
    if hit is not None:
        return hit
    value = await factory()
    await Cache.set(key, value, ttl=ttl)
    return value
