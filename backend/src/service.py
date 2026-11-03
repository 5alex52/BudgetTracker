import uuid
from typing import Dict
from typing import Generic
from typing import Optional
from typing import TypeVar
from typing import Union

from fastapi import HTTPException
from fastapi import status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from .dao import BaseDAO
from .database import async_session_maker
from .database import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    dao: BaseDAO = None
    create_chema = None
    update_chema = None

    @classmethod
    async def create(
        cls,
        schema: Union[CreateSchemaType, Dict],
        session_maker: Optional[async_sessionmaker] = None,
    ):
        if session_maker is None:
            session_maker = async_session_maker
        async with session_maker() as session:
            db_obj = await cls.dao.create(session, schema)
            if db_obj is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Object creation conflict",
                )
            await session.commit()
        return db_obj

    @classmethod
    async def update(
        cls,
        id: Union[int, uuid.UUID],
        schema,
        session_maker: Optional[async_sessionmaker] = None,
    ):
        if session_maker is None:
            session_maker = async_session_maker
        async with session_maker() as session:
            db_obj = await cls.dao.update(
                session, cls.dao.model.id == id, obj_in=schema
            )
            await session.commit()
        return db_obj

    @classmethod
    async def delete(
        cls,
        id: Union[int, uuid.UUID],
        session_maker: Optional[async_sessionmaker] = None,
    ) -> None:
        if session_maker is None:
            session_maker = async_session_maker
        async with session_maker() as session:
            try:
                await cls.dao.delete(session, cls.dao.model.id == id)
                await session.commit()
            except IntegrityError:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Object deletion conflict",
                )
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Object not found"
                )

    @classmethod
    async def get(
        cls,
        id: Union[int, uuid.UUID],
        session_maker: Optional[async_sessionmaker] = None,
    ):
        if session_maker is None:
            session_maker = async_session_maker
        async with session_maker() as session:
            db_obj = await cls.dao.find_one_or_none(session, id=id)
        if db_obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Object not found"
            )
        return db_obj

    @classmethod
    async def get_or_create(
        cls, schema, session_maker: Optional[async_sessionmaker] = None
    ):
        if session_maker is None:
            session_maker = async_session_maker
        async with session_maker() as session:
            db_obj = await cls.dao.get_or_create(session, schema)
            await session.commit()
            return db_obj

    @classmethod
    async def get_list(
        cls,
        *filter,
        offset: int = 0,
        limit: int = 100,
        session_maker: Optional[async_sessionmaker] = None,
        **filter_by,
    ):
        if session_maker is None:
            session_maker = async_session_maker
        async with session_maker() as session:
            db_obj = await cls.dao.find_all(
                session, *filter, offset=offset, limit=limit, **filter_by
            )
        return db_obj
