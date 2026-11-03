from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import sessionmaker

from .config import settings
from .constants import DB_NAMING_CONVENTION


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=DB_NAMING_CONVENTION)

    def __str__(self):
        return self.id

    @classmethod
    def pk_name(cls):
        """Pick"""
        return cls.__mapper__.primary_key[0].name

    def as_dict(self) -> dict:
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


if settings.ENVIRONMENT == "TEST":
    ASYNC_DATABASE_URL = settings.ASYNC_TEST_DATABASE_URL
    SYNC_DATABASE_URL = settings.SYNC_TEST_DATABASE_URL
    DATABASE_PARAMS = {"poolclass": NullPool}
else:
    ASYNC_DATABASE_URL = settings.ASYNC_DATABASE_URL
    SYNC_DATABASE_URL = settings.SYNC_DATABASE_URL
    DATABASE_PARAMS = {}

async_engine = create_async_engine(ASYNC_DATABASE_URL, **DATABASE_PARAMS)

async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)

sync_engine = create_engine(SYNC_DATABASE_URL, **DATABASE_PARAMS)

sync_session_maker = sessionmaker(sync_engine, expire_on_commit=False)


async def get_async_session_maker() -> async_sessionmaker:
    """FastAPI dependency returning the application session maker factory."""
    return async_session_maker
