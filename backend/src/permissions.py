from typing import Any
from typing import Optional

from fastapi import Request


class BasePermission:
    """Базовый класс для проверки прав доступа"""

    def __init__(self, request: Request, action: str):
        self.request = request
        self.action = action

    async def __call__(self, current_user: Optional[Any] = None, **kwargs) -> None:
        """Проверка прав. По умолчанию разрешает всем.

        Should raise HTTPException(403) when access is denied.
        """
        pass
