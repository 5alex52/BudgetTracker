from typing import Any
from typing import Optional
from typing import Set

from fastapi import HTTPException
from fastapi import status
from src.permissions import BasePermission


class AnalyticsPermission(BasePermission):
    """Analytics access permissions.

    Analytics is built on personal financial data, so all methods require
    authentication: there are no public reports in the service.
    """

    #: No public actions — even reference reports are calculated from user data
    PUBLIC_ACTIONS: Set[str] = set()

    #: Superuser actions: not needed, aggregates are always scoped to the user's own user_id
    SUPERUSER_ACTIONS: Set[str] = set()

    async def __call__(self, current_user: Optional[Any] = None, **kwargs) -> None:
        if self.action in self.PUBLIC_ACTIONS:
            return

        if current_user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
            )
