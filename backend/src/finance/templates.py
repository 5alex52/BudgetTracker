"""Quick entry templates: preset transaction entries.

Vertical slice of the finance app: DAO → service → viewset → router in one
module, shared layer files (``models.py``, ``schemas.py``) remain unified for
the application.
"""

import logging
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import List
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from sqlalchemy import delete
from sqlalchemy import insert
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import async_session_maker
from src.database import get_async_session_maker
from src.users.schemas import User
from src.viewset import BaseViewSet
from src.viewset import check_permissions

from .dependencies import CurrentUser
from .models import TemplateModel
from .models import TransactionModel
from .permissions import FinancePermission
from .schemas import TagInline
from .schemas import TemplateCreate
from .schemas import TemplateResponse
from .schemas import TemplateUpdate
from .schemas import TransactionCreate
from .schemas import TransactionResponse
from .schemas import TransactionType
from .service import TransactionService
from .tags import ensure_tags_owned

logger = logging.getLogger(__name__)

__all__ = ["TemplateDAO", "TemplateService", "TemplateViewSet", "templates_router"]


def _not_found(detail: str = "Template not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class TemplateDAO:
    """Data access for user templates."""

    model = TemplateModel

    @classmethod
    async def find_all_by_user(
        cls, session: AsyncSession, user_id: uuid.UUID
    ) -> List[TemplateModel]:
        stmt = (
            select(TemplateModel)
            .where(TemplateModel.user_id == user_id)
            .order_by(TemplateModel.usage_count.desc(), TemplateModel.name)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def find_one_by_user(
        cls, session: AsyncSession, template_id: int, user_id: uuid.UUID
    ) -> Optional[TemplateModel]:
        stmt = select(TemplateModel).where(
            TemplateModel.id == template_id, TemplateModel.user_id == user_id
        )
        result = await session.execute(stmt)
        return result.scalars().one_or_none()

    @classmethod
    async def tag_ids_of(cls, session: AsyncSession, template_id: int) -> List[int]:
        from .models import (
            template_tags as table,
        )  # local import: table is declared in models

        stmt = select(table.c.tag_id).where(table.c.template_id == template_id)
        result = await session.execute(stmt)
        return [row for row in result.scalars().all()]

    @classmethod
    async def set_tags(
        cls, session: AsyncSession, template_id: int, tag_ids: Sequence[int]
    ) -> None:
        from .models import template_tags as table

        await session.execute(delete(table).where(table.c.template_id == template_id))
        if tag_ids:
            await session.execute(
                insert(table),
                [
                    {"template_id": template_id, "tag_id": tag_id}
                    for tag_id in set(tag_ids)
                ],
            )


class TemplateService:
    """Templates: CRUD scoped to user plus template application."""

    dao = TemplateDAO

    @classmethod
    async def get_list_by_user(
        cls, user_id: uuid.UUID, session_maker: Optional[async_sessionmaker] = None
    ) -> List[TemplateResponse]:
        maker = session_maker or async_session_maker
        async with maker() as session:
            templates = await cls.dao.find_all_by_user(session, user_id)
            responses = []
            for template in templates:
                tag_ids = await cls.dao.tag_ids_of(session, template.id)
                responses.append(await cls._to_response(session, template, tag_ids))
        return responses

    @classmethod
    async def _to_response(
        cls, session: AsyncSession, template: TemplateModel, tag_ids: List[int]
    ) -> TemplateResponse:
        from .models import TagModel

        tags: List[TagInline] = []
        if tag_ids:
            stmt = select(TagModel).where(TagModel.id.in_(tag_ids))
            result = await session.execute(stmt)
            tags = [
                TagInline(id=tag.id, name=tag.name, color=tag.color)
                for tag in result.scalars().all()
            ]
        return TemplateResponse(
            id=template.id,
            name=template.name,
            type=template.type,
            amount=template.amount,
            currency_id=template.currency_id,
            account_id=template.account_id,
            category_id=template.category_id,
            note=template.note,
            icon=template.icon,
            usage_count=template.usage_count,
            tags=tags,
        )

    @classmethod
    async def create_for_user(
        cls,
        schema: TemplateCreate,
        user_id: uuid.UUID,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> TemplateResponse:
        maker = session_maker or async_session_maker
        async with maker() as session:
            await cls._validate_links(session, schema, user_id, session_maker=maker)
            data = schema.model_dump(exclude={"tag_ids"})
            template = TemplateModel(user_id=user_id, **data)
            session.add(template)
            await session.flush()
            await cls.dao.set_tags(session, template.id, schema.tag_ids)
            await session.commit()
            await session.refresh(template)
            return await cls._to_response(session, template, list(schema.tag_ids))

    @classmethod
    async def get_by_user(
        cls,
        template_id: int,
        user_id: uuid.UUID,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> TemplateResponse:
        maker = session_maker or async_session_maker
        async with maker() as session:
            template = await cls.dao.find_one_by_user(session, template_id, user_id)
            if template is None:
                raise _not_found()
            return await cls._to_response(
                session, template, await cls.dao.tag_ids_of(session, template_id)
            )

    @classmethod
    async def update_for_user(
        cls,
        template_id: int,
        schema: TemplateUpdate,
        user_id: uuid.UUID,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> TemplateResponse:
        maker = session_maker or async_session_maker
        async with maker() as session:
            template = await cls.dao.find_one_by_user(session, template_id, user_id)
            if template is None:
                raise _not_found()

            data = schema.model_dump(exclude_unset=True)
            tag_ids = data.pop("tag_ids", None)
            # Validate the resulting template state: partial update must not
            # bypass account, category and currency checks.
            await cls._validate_links(
                session,
                TemplateCreate(
                    name=data.get("name", template.name),
                    type=data.get("type", template.type),
                    amount=data.get("amount", template.amount),
                    currency_id=data.get("currency_id", template.currency_id),
                    account_id=data.get("account_id", template.account_id),
                    category_id=data.get("category_id", template.category_id),
                    note=data.get("note", template.note),
                    icon=data.get("icon", template.icon),
                    tag_ids=(
                        tag_ids
                        if tag_ids is not None
                        else await cls.dao.tag_ids_of(session, template_id)
                    ),
                ),
                user_id,
                session_maker=maker,
            )
            for field, value in data.items():
                setattr(template, field, value)
            if tag_ids is not None:
                await cls.dao.set_tags(session, template_id, tag_ids)
            await session.commit()
            await session.refresh(template)
            return await cls._to_response(
                session, template, await cls.dao.tag_ids_of(session, template_id)
            )

    @classmethod
    async def delete_for_user(
        cls,
        template_id: int,
        user_id: uuid.UUID,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> None:
        maker = session_maker or async_session_maker
        async with maker() as session:
            template = await cls.dao.find_one_by_user(session, template_id, user_id)
            if template is None:
                raise _not_found()
            await session.delete(template)
            await session.commit()

    @classmethod
    async def apply(
        cls,
        template_id: int,
        user_id: uuid.UUID,
        date: Optional[datetime] = None,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> TransactionModel:
        """Creates a transaction from template and increments its usage counter."""
        maker = session_maker or async_session_maker
        async with maker() as session:
            template = await cls.dao.find_one_by_user(session, template_id, user_id)
            if template is None:
                raise _not_found()
            tag_ids = await cls.dao.tag_ids_of(session, template_id)
            transaction_schema = TransactionCreate(
                account_id=template.account_id,
                category_id=template.category_id,
                amount=template.amount,
                currency_id=template.currency_id,
                type=template.type,
                date=date or datetime.now(),
                note=template.note,
                tag_ids=tag_ids,
            )
            template.usage_count += 1
            await session.commit()

        # Transaction is created by the same service as a regular one: rules and balances in one place
        return await TransactionService.create_for_user(
            schema=transaction_schema, user_id=user_id, session_maker=maker
        )

    @classmethod
    async def _validate_links(
        cls,
        session: AsyncSession,
        schema: TemplateCreate,
        user_id: uuid.UUID,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> None:
        from .models import AccountModel
        from .models import CategoryModel

        account = await session.get(AccountModel, schema.account_id)
        if account is None or account.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown account"
            )
        category = await session.get(CategoryModel, schema.category_id)
        if category is None or category.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown category"
            )
        if schema.type == TransactionType.INCOME and category.type.value != "income":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Category type mismatch"
            )
        if schema.type == TransactionType.EXPENSE and category.type.value != "expense":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Category type mismatch"
            )
        await ensure_tags_owned(session, schema.tag_ids, user_id)


class TemplateViewSet(BaseViewSet[int, TemplateCreate, TemplateUpdate]):
    permission = FinancePermission
    service = TemplateService

    @classmethod
    @check_permissions(action="list_templates")
    async def list(
        cls,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> List[TemplateResponse]:
        return await cls.service.get_list_by_user(
            user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="retrieve_template")
    async def retrieve(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> TemplateResponse:
        return await cls.service.get_by_user(
            template_id=obj_id, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="create_template")
    async def create(
        cls,
        obj_data: TemplateCreate,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> TemplateResponse:
        return await cls.service.create_for_user(
            schema=obj_data, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="update_template")
    async def update(
        cls,
        obj_id: int,
        obj_data: TemplateUpdate,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> TemplateResponse:
        return await cls.service.update_for_user(
            template_id=obj_id,
            schema=obj_data,
            user_id=user.id,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="delete_template")
    async def delete(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> None:
        await cls.service.delete_for_user(
            template_id=obj_id, user_id=user.id, session_maker=session_maker
        )

    @classmethod
    @check_permissions(action="apply_template")
    async def apply(
        cls,
        obj_id: int,
        user: User,
        date: Optional[datetime] = None,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> TransactionModel:
        return await cls.service.apply(
            template_id=obj_id, user_id=user.id, date=date, session_maker=session_maker
        )


templates_router = APIRouter(prefix="/api/finance/templates", tags=["Templates"])


@templates_router.get(
    "/", status_code=status.HTTP_200_OK, response_model=List[TemplateResponse]
)
async def list_templates(
    request: Request,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[TemplateResponse]:
    """Quick entry templates, most used first."""
    return await TemplateViewSet.list(
        request=request, user=user, session_maker=session_maker
    )


@templates_router.post(
    "/", status_code=status.HTTP_201_CREATED, response_model=TemplateResponse
)
async def create_template(
    request: Request,
    user: CurrentUser,
    payload: TemplateCreate,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> TemplateResponse:
    """New template; account, category and tags must belong to the user."""
    return await TemplateViewSet.create(
        request=request, user=user, obj_data=payload, session_maker=session_maker
    )


@templates_router.get(
    "/{template_id}", status_code=status.HTTP_200_OK, response_model=TemplateResponse
)
async def get_template(
    request: Request,
    user: CurrentUser,
    template_id: int,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> TemplateResponse:
    """Template by ID."""
    return await TemplateViewSet.retrieve(
        request=request, user=user, obj_id=template_id, session_maker=session_maker
    )


@templates_router.patch(
    "/{template_id}", status_code=status.HTTP_200_OK, response_model=TemplateResponse
)
async def update_template(
    request: Request,
    user: CurrentUser,
    template_id: int,
    payload: TemplateUpdate,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> TemplateResponse:
    """Update a template."""
    return await TemplateViewSet.update(
        request=request,
        user=user,
        obj_id=template_id,
        obj_data=payload,
        session_maker=session_maker,
    )


@templates_router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    request: Request,
    user: CurrentUser,
    template_id: int,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> None:
    """Delete a template; transactions created from it remain."""
    await TemplateViewSet.delete(
        request=request, user=user, obj_id=template_id, session_maker=session_maker
    )


@templates_router.post(
    "/{template_id}/apply",
    status_code=status.HTTP_201_CREATED,
    response_model=TransactionResponse,
)
async def apply_template(
    request: Request,
    user: CurrentUser,
    template_id: int,
    date: Optional[datetime] = None,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> TransactionModel:
    """Creates a transaction from template: date is application time if not provided."""
    return await TemplateViewSet.apply(
        request=request,
        user=user,
        obj_id=template_id,
        date=date,
        session_maker=session_maker,
    )
