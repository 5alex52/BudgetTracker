"""Кеш поверх Redis.

Заготовка уже была: клиент создаётся в lifespan приложения и в ``src/celery.py``.
Здесь — тонкая обёртка, которой пользуются сервисы, чтобы не тянуть один и тот
же агрегат из базы на каждый рендер страницы.

Главное правило: **кеш не должен ломать приложение**. Если Redis не подключён
(локальная разработка, упавший инстанс), все методы становятся no-op и сервис
считает данные как обычно.
"""

import hashlib
import json
import logging
from typing import Any
from typing import Optional

logger = logging.getLogger(__name__)

#: Префикс всех ключей приложения: в одном Redis могут жить и другие проекты
PREFIX = "bt"


class Cache:
    """Асинхронный кеш с безопасной деградацией."""

    _client: Any = None

    # ------------------------------------------------------------------ #
    #  Подключение
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
    #  Ключи
    # ------------------------------------------------------------------ #

    @staticmethod
    def make_key(scope: str, **parts: Any) -> str:
        """Детерминированный ключ: ``bt:scope:hash(params)``.

        Параметры хешируются, поэтому длинные даты и списки не раздувают ключ,
        а порядок аргументов не влияет на попадание в кеш.
        """
        payload = json.dumps(parts, sort_keys=True, default=str, ensure_ascii=False)
        digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:20]
        return f"{PREFIX}:{scope}:{digest}"

    # ------------------------------------------------------------------ #
    #  Чтение и запись
    # ------------------------------------------------------------------ #

    @classmethod
    async def get(cls, key: str) -> Optional[Any]:
        if cls._client is None:
            return None
        try:
            raw = await cls._client.get(key)
        except Exception as caught:  # noqa: BLE001 — кеш не должен ронять запрос
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
        """Сбрасывает весь раздел: нужен после записи, которая влияет на агрегаты.

        ``SCAN`` вместо ``KEYS``: второй блокирует Redis на больших базах.
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
    """Вернуть значение из кеша или посчитать и положить.

    ``factory`` — корутина без аргументов. Ошибки вычисления не кешируются.
    """
    key = Cache.make_key(scope, **key_parts)
    hit = await Cache.get(key)
    if hit is not None:
        return hit
    value = await factory()
    await Cache.set(key, value, ttl=ttl)
    return value
