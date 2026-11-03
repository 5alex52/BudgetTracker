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
    """Декоратор для проверки прав доступа.

    Перед вызовом метода ViewSet-а инстанцируется ``permission``-класс ViewSet-а и
    вызывается с указанным действием. Permission-класс может бросить HTTPException(403).
    """

    def decorator(func):
        # request пробрасывается в метод, только если он объявлен в его сигнатуре явно,
        # иначе он бы попал в **kwargs и был бы передан в сервис как лишний аргумент.
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
    """Базовый ViewSet для обработки CRUD операций"""

    service: BaseService = None
    permission = BasePermission

    @classmethod
    async def create(
        cls,
        obj_data: CreateSchemaType,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ):
        """Создание нового объекта"""
        return await cls.service.create(schema=obj_data, session_maker=session_maker, **kwargs)

    @classmethod
    async def retrieve(
        cls,
        obj_id: ModelType,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ):
        """Получение одного объекта"""
        return await cls.service.get(id=obj_id, session_maker=session_maker)

    @classmethod
    async def update(
        cls,
        obj_id: ModelType,
        obj_data: UpdateSchemaType,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ):
        """Обновление объекта"""
        return await cls.service.update(id=obj_id, schema=obj_data, session_maker=session_maker)

    @classmethod
    async def delete(
        cls,
        obj_id: ModelType,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ):
        """Удаление объекта"""
        await cls.service.delete(id=obj_id, session_maker=session_maker)

    @classmethod
    async def list(
        cls,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ):
        """Список объектов"""
        return await cls.service.get_list(session_maker=session_maker)
