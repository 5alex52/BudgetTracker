from typing import Any
from typing import Optional

from fastapi import Request


class BasePermission:
    """Base class for access permission checks"""

    def __init__(self, request: Request, action: str):
        self.request = request
        self.action = action

    async def __call__(self, current_user: Optional[Any] = None, **kwargs) -> None:
        """Permission check. Allows everyone by default.

        Should raise HTTPException(403) when access is denied.
        """
        pass
