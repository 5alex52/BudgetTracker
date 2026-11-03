from typing import Any
from typing import Optional
from typing import Set

from fastapi import HTTPException
from fastapi import status
from src.permissions import BasePermission


class FinancePermission(BasePermission):
    """Права доступа для финансовых операций.

    Финансовые данные всегда принадлежат конкретному пользователю, поэтому любой
    непубличный метод требует аутентифицированного пользователя. Управление
    справочником валют (создание/изменение/удаление) доступно только суперпользователю.
    """

    #: Действия, доступные без аутентификации
    PUBLIC_ACTIONS: Set[str] = {
        "list_currencies",
        "retrieve_currency",
        "currency_rates",
    }

    #: Действия, доступные только суперпользователю
    SUPERUSER_ACTIONS: Set[str] = {
        "create_currency",
        "update_currency",
        "delete_currency",
    }

    async def __call__(self, current_user: Optional[Any] = None, **kwargs) -> None:
        if self.action in self.PUBLIC_ACTIONS:
            return

        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )

        if self.action in self.SUPERUSER_ACTIONS and not getattr(
            current_user, "is_superuser", False
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges"
            )
