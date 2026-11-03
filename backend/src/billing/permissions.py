from typing import Any
from typing import Optional
from typing import Set

from fastapi import HTTPException
from fastapi import status
from src.permissions import BasePermission


class BillingPermission(BasePermission):
    """Права доступа к биллингу.

    Список тарифов и провайдеров — публичный: он нужен до оформления подписки.
    Всё, что касается конкретного пользователя, требует аутентификации.
    """

    PUBLIC_ACTIONS: Set[str] = {"list_plans", "list_providers"}

    #: Изменение каталога тарифов — только суперпользователь
    SUPERUSER_ACTIONS: Set[str] = set()

    async def __call__(self, current_user: Optional[Any] = None, **kwargs) -> None:
        if self.action in self.PUBLIC_ACTIONS:
            return

        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )
