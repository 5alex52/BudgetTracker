from collections.abc import Callable
from uuid import UUID

from fastapi import Depends
from fastapi import Request
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.database import get_async_session_maker
from src.permissions import BasePermission


def check_permissions(action: str):
    """Декоратор для проверки прав доступа"""

    def decorator(func: Callable):
        async def wrapper(
            request: Request,
            session_maker: async_sessionmaker = Depends(get_async_session_maker),
            *args,
            **kwargs,
        ):
            permission = BasePermission(request, action)
            await permission(**kwargs)
            return await func(
                request=request, session_maker=session_maker, *args, **kwargs
            )

        return wrapper

    return decorator
