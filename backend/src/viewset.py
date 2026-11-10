import inspect
import logging
from typing import Generic
from typing import Optional
from typing import TypeVar

from fastapi import Depends
from fastapi import Request
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.database import get_async_session_maker
from src.permissions import BasePermission
from src.service import BaseService

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

__all__ = ["BasePermission", "BaseViewSet", "check_permissions"]


def check_permissions(action: str):
    """Decorator for access control checks.

    Before calling a ViewSet method, the ViewSet's ``permission`` class is instantiated
    and invoked with the specified action. The permission class may raise HTTPException(403).
    """

    def decorator(func):
        # Request is passed to the method only if it's explicitly declared in its signature,
        # otherwise it would end up in **kwargs and be passed to the service as an extra argument.
        accepts_request = "request" in inspect.signature(func).parameters

        async def wrapper(cls, *args, request: Optional[Request] = None, **kwargs):
            permission_cls = getattr(cls, "permission", BasePermission)
            permission = permission_cls(request=request, action=action)
            await permission(current_user=kwargs.get("user"), **kwargs)
            if accepts_request:
                kwargs["request"] = request
            return await func(cls, *args, **kwargs)

        return wrapper

    return decorator


class BaseViewSet(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base ViewSet for handling CRUD operations"""

    service: BaseService = None
    permission = BasePermission

    @classmethod
    async def create(
        cls,
        obj_data: CreateSchemaType,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ):
        """Create a new object"""
        return await cls.service.create(
            schema=obj_data, session_maker=session_maker, **kwargs
        )

    @classmethod
    async def retrieve(
        cls,
        obj_id: ModelType,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ):
        """Retrieve a single object"""
        return await cls.service.get(id=obj_id, session_maker=session_maker)

    @classmethod
    async def update(
        cls,
        obj_id: ModelType,
        obj_data: UpdateSchemaType,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ):
        """Update an object"""
        return await cls.service.update(
            id=obj_id, schema=obj_data, session_maker=session_maker
        )

    @classmethod
    async def delete(
        cls,
        obj_id: ModelType,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ):
        """Delete an object"""
        await cls.service.delete(id=obj_id, session_maker=session_maker)

    @classmethod
    async def list(
        cls,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ):
        """List objects"""
        return await cls.service.get_list(session_maker=session_maker)
