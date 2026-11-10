from typing import Any
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import TypeVar
from typing import Union

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func
from starlette import status

from .database import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseDAO(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    model = None

    @classmethod
    async def find_one_or_none(cls, session: AsyncSession, *filter, **filter_by) -> Optional[ModelType]:
        stmt = select(cls.model).filter(*filter).filter_by(**filter_by)
        result = await session.execute(stmt)
        return result.scalars().one_or_none()

    @classmethod
    async def find_all(
        cls,
        session: AsyncSession,
        *filter,
        offset: int = 0,
        limit: int = 100,
        **filter_by,
    ) -> List[ModelType]:
        stmt = select(cls.model).filter(*filter).filter_by(**filter_by).offset(offset).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        obj_in: Union[CreateSchemaType, Dict[str, Any]],
        http_exc_text: str = "Record with some unique data exists",
    ) -> Optional[ModelType]:
        if isinstance(obj_in, dict):
            create_data = obj_in
        else:
            create_data = obj_in.model_dump(exclude_unset=True)
        try:
            stmt = insert(cls.model).values(**create_data).returning(cls.model)
            result = await session.execute(stmt)
            return result.scalars().first()
        except (SQLAlchemyError, Exception, IntegrityError) as e:
            if isinstance(e, SQLAlchemyError):
                msg = "Database Exc: Cannot insert data into table"
                print(f"{e}")
            elif isinstance(e, Exception):
                print(f"{e}")
                msg = "Unknown Exc: Cannot insert data into table"
            elif isinstance(e, IntegrityError):
                raise HTTPException(detail=http_exc_text, status_code=status.HTTP_400_BAD_REQUEST)
            print(msg)
            return None

    @classmethod
    async def add(
        cls,
        session: AsyncSession,
        obj_in: Union[CreateSchemaType, Dict[str, Any]],
        http_exc_text: str = "Record with some unique data exists",
    ) -> Optional[ModelType]:
        """Alias for create() kept for readability in get_or_create()."""
        return await cls.create(session, obj_in, http_exc_text=http_exc_text)

    @classmethod
    async def get_or_create(
        cls, session: AsyncSession, defaults: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Optional[ModelType]:
        # Schema can be passed as a whole: its fields are used as both filter and creation data
        if isinstance(defaults, BaseModel):
            kwargs.update(defaults.model_dump())
            defaults = None

        instance = await cls.find_one_or_none(session, **kwargs)
        if instance:
            return instance
        if defaults:
            kwargs.update(defaults)
        instance = await cls.add(session, kwargs)
        return instance

    @classmethod
    async def delete(cls, session: AsyncSession, *filter, **filter_by) -> None:
        obj = await cls.find_one_or_none(session, *filter, **filter_by)
        if obj is None:
            raise ValueError
        stmt = delete(cls.model).filter(*filter).filter_by(**filter_by)
        await session.execute(stmt)

    @classmethod
    async def delete_all(cls, session: AsyncSession, *filter, **filter_by) -> None:
        stmt = delete(cls.model).filter(*filter).filter_by(**filter_by)
        await session.execute(stmt)

    @classmethod
    async def update(
        cls,
        session: AsyncSession,
        *where,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]],
    ) -> Optional[ModelType]:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        if not update_data:
            # Empty PATCH should not trigger an UPDATE without SET
            db_obj = await cls.find_one_or_none(session, *where)
            if db_obj is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
            return db_obj
        stmt = update(cls.model).where(*where).values(**update_data).returning(cls.model)
        result = await session.execute(stmt)
        db_obj = result.scalars().one_or_none()
        if db_obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Object not found")
        return db_obj

    @classmethod
    async def add_bulk(cls, session: AsyncSession, data: List[Dict[str, Any]]):
        try:
            result = await session.execute(insert(cls.model).returning(cls.model), data)
            return result.scalars().all()
        except (SQLAlchemyError, Exception) as e:
            if isinstance(e, SQLAlchemyError):
                msg = "Database Exc"
            elif isinstance(e, Exception):
                msg = "Unknown Exc"
            msg += ": Cannot bulk insert data into table"
            return None

    @classmethod
    async def update_bulk(cls, session: AsyncSession, data: List[Dict[str, Any]]):
        try:
            stmt = update(cls.model)
            await session.execute(update(cls.model), data)
        except (SQLAlchemyError, Exception) as e:
            if isinstance(e, SQLAlchemyError):
                msg = "Database Exc"
            elif isinstance(e, Exception):
                msg = "Unknown Exc"
            msg += ": Cannot bulk update data into table"
            print(msg)
            return None

    @classmethod
    async def count(cls, session: AsyncSession, *filter, **filter_by):
        stmt = select(func.count()).select_from(cls.model).filter(*filter).filter_by(**filter_by)
        result = await session.execute(stmt)
        return result.scalar()
