from typing import Any
from typing import Optional
from typing import Set

from fastapi import HTTPException
from fastapi import status
from src.permissions import BasePermission


class AnalyticsPermission(BasePermission):
    """Права доступа к аналитике.

    Аналитика строится по личным финансовым данным, поэтому все методы требуют
    аутентификации: публичных отчётов в сервисе нет.
    """

    #: Публичных действий нет — даже справочные отчёты считаются по данным пользователя
    PUBLIC_ACTIONS: Set[str] = set()

    #: Действия для суперпользователя: не нужны, агрегаты всегда по своему user_id
    SUPERUSER_ACTIONS: Set[str] = set()

    async def __call__(self, current_user: Optional[Any] = None, **kwargs) -> None:
        if self.action in self.PUBLIC_ACTIONS:
            return

        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )
