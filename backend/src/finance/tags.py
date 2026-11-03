"""Метки записей: вертикальный срез приложения finance.

Метки — часть финансового домена, поэтому живут в приложении ``finance``, но
отдельным модулем: слой модели/схемы остаётся общим (``models.py``, ``schemas.py``),
а DAO → сервис → viewset → роутер для меток собраны здесь, чтобы не раздувать
общие файлы слоёв.
"""

import logging
import uuid
from collections.abc import Sequence
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from sqlalchemy import delete
from sqlalchemy import func
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.database import async_session_maker
from src.database import get_async_session_maker
from src.users.schemas import User
from src.viewset import BaseViewSet
from src.viewset import check_permissions

from .dependencies import CurrentUser
from .models import TagModel
from .models import transaction_tags
from .models import TransactionModel
from .permissions import FinancePermission
from .schemas import TagCreate
from .schemas import TagResponse
from .schemas import TagUpdate

logger = logging.getLogger(__name__)

__all__ = [
    "TagDAO",
    "TagService",
    "TagViewSet",
    "tags_router",
    "attach_tags",
    "load_tags",
    "ensure_tags_owned",
    "tag_ids_of",
]


def _not_found(detail: str = "Tag not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class TagDAO:
    """Доступ к меткам и их связи с записями."""

    model = TagModel

    @classmethod
    async def find_all_by_user(cls, session: AsyncSession, user_id: uuid.UUID) -> List:
        """Метки пользователя со счётчиком записей, отсортированные по популярности."""
        stmt = (
            select(
                TagModel,
                func.count(transaction_tags.c.transaction_id).label(
                    "transactions_count"
                ),
            )
            .outerjoin(transaction_tags, transaction_tags.c.tag_id == TagModel.id)
            .where(TagModel.user_id == user_id)
            .group_by(TagModel.id)
            .order_by(
                func.count(transaction_tags.c.transaction_id).desc(), TagModel.name
            )
        )
        result = await session.execute(stmt)
        return list(result.all())

    @classmethod
    async def find_one_by_user(
        cls, session: AsyncSession, tag_id: int, user_id: uuid.UUID
    ) -> Optional[TagModel]:
        stmt = select(TagModel).where(
            TagModel.id == tag_id, TagModel.user_id == user_id
        )
        result = await session.execute(stmt)
        return result.scalars().one_or_none()

    @classmethod
    async def find_many_by_ids(
        cls, session: AsyncSession, tag_ids: Sequence[int], user_id: uuid.UUID
    ) -> List[TagModel]:
        """Метки пользователя по списку идентификаторов — чужие молча отбрасываются."""
        if not tag_ids:
            return []
        stmt = select(TagModel).where(
            TagModel.id.in_(list(tag_ids)), TagModel.user_id == user_id
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def find_by_name(
        cls, session: AsyncSession, name: str, user_id: uuid.UUID
    ) -> Optional[TagModel]:
        stmt = select(TagModel).where(
            TagModel.name == name, TagModel.user_id == user_id
        )
        result = await session.execute(stmt)
        return result.scalars().one_or_none()

    @classmethod
    async def count_for_transaction(
        cls, session: AsyncSession, transaction_id: int
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(transaction_tags)
            .where(transaction_tags.c.transaction_id == transaction_id)
        )
        result = await session.execute(stmt)
        return int(result.scalar() or 0)


async def load_tags(
    session: AsyncSession, transaction: TransactionModel
) -> List[TagModel]:
    """Подтягивает метки записи: без этого ответ сериализуется без них."""
    stmt = (
        select(TransactionModel)
        .where(TransactionModel.id == transaction.id)
        .options(selectinload(TransactionModel.tags))
    )
    result = await session.execute(stmt)
    loaded = result.scalars().one()
    return list(loaded.tags)


async def ensure_tags_owned(
    session: AsyncSession, tag_ids: Sequence[int], user_id: uuid.UUID
) -> List[TagModel]:
    """Проверяет, что все метки принадлежат пользователю."""
    if not tag_ids:
        return []
    tags = await TagDAO.find_many_by_ids(session, tag_ids, user_id)
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown tag ids"
        )
    return tags


async def tag_ids_of(session: AsyncSession, transaction_id: int) -> List[int]:
    """Идентификаторы меток записи.

    Отдельным запросом, а не через связь ORM: обращение к ``transaction.tags`` в
    async-сессии при неподгруженной связи требует IO и падает вне greenlet.
    """
    stmt = select(transaction_tags.c.tag_id).where(
        transaction_tags.c.transaction_id == transaction_id
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def attach_tags(
    session: AsyncSession, transaction_id: int, tag_ids: Sequence[int]
) -> None:
    """Перевешивает метки записи на новый набор (пустой список — снять все)."""
    await session.execute(
        delete(transaction_tags).where(
            transaction_tags.c.transaction_id == transaction_id
        )
    )
    if tag_ids:
        await session.execute(
            insert(transaction_tags),
            [
                {"transaction_id": transaction_id, "tag_id": tag_id}
                for tag_id in set(tag_ids)
            ],
        )


class TagService:
    """Операции с метками; всегда в разрезе пользователя."""

    dao = TagDAO

    @classmethod
    async def get_list_by_user(
        cls, user_id: uuid.UUID, session_maker: Optional[async_sessionmaker] = None
    ) -> List[TagResponse]:
        maker = session_maker or async_session_maker
        async with maker() as session:
            rows = await cls.dao.find_all_by_user(session, user_id)
        return [
            TagResponse(
                id=tag.id, name=tag.name, color=tag.color, transactions_count=int(count)
            )
            for tag, count in rows
        ]

    @classmethod
    async def create_for_user(
        cls,
        schema: TagCreate,
        user_id: uuid.UUID,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> TagModel:
        maker = session_maker or async_session_maker
        async with maker() as session:
            if await cls.dao.find_by_name(session, schema.name, user_id) is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Tag name already used"
                )
            tag = cls.dao.model(user_id=user_id, name=schema.name, color=schema.color)
            session.add(tag)
            await session.commit()
            await session.refresh(tag)
        return tag

    @classmethod
    async def get_by_user(
        cls,
        tag_id: int,
        user_id: uuid.UUID,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> TagModel:
        maker = session_maker or async_session_maker
        async with maker() as session:
            tag = await cls.dao.find_one_by_user(session, tag_id, user_id)
            if tag is None:
                raise _not_found()
            return tag

    @classmethod
    async def update_for_user(
        cls,
        tag_id: int,
        schema: TagUpdate,
        user_id: uuid.UUID,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> TagModel:
        maker = session_maker or async_session_maker
        async with maker() as session:
            tag = await cls.dao.find_one_by_user(session, tag_id, user_id)
            if tag is None:
                raise _not_found()
            data = schema.model_dump(exclude_unset=True)
            if "name" in data and data["name"] != tag.name:
                if (
                    await cls.dao.find_by_name(session, data["name"], user_id)
                    is not None
                ):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Tag name already used",
                    )
            for field, value in data.items():
                setattr(tag, field, value)
            await session.commit()
            await session.refresh(tag)
        return tag

    @classmethod
    async def delete_for_user(
        cls,
        tag_id: int,
        user_id: uuid.UUID,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> None:
        maker = session_maker or async_session_maker
        async with maker() as session:
            tag = await cls.dao.find_one_by_user(session, tag_id, user_id)
            if tag is None:
                raise _not_found()
            await session.delete(tag)
            await session.commit()


class TagViewSet(BaseViewSet[int, TagCreate, TagUpdate]):
    permission = FinancePermission
    service = TagService

    @classmethod
    @check_permissions(action="list_tags")
    async def list(
        cls,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> List[TagResponse]:
        return await cls.service.get_list_by_user(
            user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="retrieve_tag")
    async def retrieve(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> TagModel:
        return await cls.service.get_by_user(
            tag_id=obj_id, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="create_tag")
    async def create(
        cls,
        obj_data: TagCreate,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> TagModel:
        return await cls.service.create_for_user(
            schema=obj_data, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="update_tag")
    async def update(
        cls,
        obj_id: int,
        obj_data: TagUpdate,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> TagModel:
        return await cls.service.update_for_user(
            tag_id=obj_id, schema=obj_data, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="delete_tag")
    async def delete(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> None:
        await cls.service.delete_for_user(
            tag_id=obj_id, user_id=user.id, session_maker=session_maker
        )


tags_router = APIRouter(prefix="/api/finance/tags", tags=["Tags"])


@tags_router.get("/", status_code=status.HTTP_200_OK, response_model=List[TagResponse])
async def list_tags(
    request: Request,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[TagResponse]:
    """Метки пользователя со счётчиком записей."""
    return await TagViewSet.list(
        request=request, user=user, session_maker=session_maker
    )


@tags_router.post("/", status_code=status.HTTP_201_CREATED, response_model=TagResponse)
async def create_tag(
    request: Request,
    user: CurrentUser,
    payload: TagCreate,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> TagModel:
    """Новая метка; имя уникально в пределах пользователя."""
    return await TagViewSet.create(
        request=request, user=user, obj_data=payload, session_maker=session_maker
    )


@tags_router.get(
    "/{tag_id}", status_code=status.HTTP_200_OK, response_model=TagResponse
)
async def get_tag(
    request: Request,
    user: CurrentUser,
    tag_id: int,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> TagModel:
    """Метка по идентификатору."""
    return await TagViewSet.retrieve(
        request=request, user=user, obj_id=tag_id, session_maker=session_maker
    )


@tags_router.patch(
    "/{tag_id}", status_code=status.HTTP_200_OK, response_model=TagResponse
)
async def update_tag(
    request: Request,
    user: CurrentUser,
    tag_id: int,
    payload: TagUpdate,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> TagModel:
    """Переименование метки или смена цвета."""
    return await TagViewSet.update(
        request=request,
        user=user,
        obj_id=tag_id,
        obj_data=payload,
        session_maker=session_maker,
    )


@tags_router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    request: Request,
    user: CurrentUser,
    tag_id: int,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> None:
    """Удаление метки; связи с записями уходят каскадом, сами записи остаются."""
    await TagViewSet.delete(
        request=request, user=user, obj_id=tag_id, session_maker=session_maker
    )
