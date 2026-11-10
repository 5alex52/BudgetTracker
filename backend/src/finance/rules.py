"""Auto-categorization rules and their engine.

A rule is a condition on a record (note or amount) and a set of actions: change
the category, attach a tag, hide the record from statistics. The engine is
applied in two places: when creating a record
(``TransactionService.create_for_user``) and on the user's request to already
existing records (``POST /rules/apply``).
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
from fastapi import Query
from fastapi import Request
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import async_session_maker
from src.database import get_async_session_maker
from src.users.schemas import User
from src.viewset import BaseViewSet
from src.viewset import check_permissions

from .dependencies import CurrentUser
from .models import CategoryModel
from .models import RuleModel
from .models import TagModel
from .models import TransactionModel
from .permissions import FinancePermission
from .schemas import RuleApplyResult
from .schemas import RuleCreate
from .schemas import RuleField
from .schemas import RuleOperator
from .schemas import RuleResponse
from .schemas import RuleUpdate
from .schemas import TransactionType
from .tags import attach_tags
from .tags import tag_ids_of

logger = logging.getLogger(__name__)

__all__ = [
    "RuleDAO",
    "RuleService",
    "RuleViewSet",
    "rules_router",
    "RuleEngine",
    "match_rule",
    "apply_rules",
]


def _not_found(detail: str = "Rule not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def match_rule(rule: RuleModel, note: Optional[str], amount: float) -> bool:
    """Check the rule condition.

    The note is compared case-insensitively: the user writes "Store" and "store"
    with the same meaning, and the rule must match both.
    """
    if rule.field == RuleField.NOTE:
        haystack = (note or "").lower()
        needle = (rule.value or "").lower()
        if rule.operator == RuleOperator.CONTAINS:
            return needle in haystack
        if rule.operator == RuleOperator.EQUALS:
            return haystack == needle
        # Numeric operators do not apply to text
        return False

    try:
        threshold = float(rule.value)
    except (TypeError, ValueError):
        return False
    if rule.operator == RuleOperator.GREATER:
        return amount > threshold
    if rule.operator == RuleOperator.LESS:
        return amount < threshold
    if rule.operator == RuleOperator.EQUALS:
        return amount == threshold
    return False


async def apply_rules(
    session: AsyncSession,
    transaction: TransactionModel,
    user_id: uuid.UUID,
    rules: Optional[Sequence[RuleModel]] = None,
) -> List[int]:
    """Apply active rules to a record. Returns ids of the rules that matched.

    Rules are applied in ascending priority order, so a higher-priority rule can
    override a lower-priority one.
    """
    if rules is None:
        rules = await RuleDAO.find_active_by_user(session, user_id)

    matched: List[int] = []
    for rule in rules:
        if not match_rule(rule, transaction.note, transaction.amount):
            continue
        matched.append(rule.id)
        # A transfer has a service category: a rule must not replace it with an expense
        if rule.set_category_id is not None and transaction.type != TransactionType.TRANSFER:
            transaction.category_id = rule.set_category_id
        if rule.exclude_from_statistics:
            transaction.is_excluded = True
        if rule.add_tag_id is not None:
            current = set(await tag_ids_of(session, transaction.id))
            if rule.add_tag_id not in current:
                await attach_tags(session, transaction.id, sorted(current | {rule.add_tag_id}))
    if matched:
        await session.flush()
    return matched


class RuleDAO:
    """Access to user rules."""

    model = RuleModel

    @classmethod
    def _stmt(cls, user_id: uuid.UUID):
        return select(RuleModel).where(RuleModel.user_id == user_id)

    @classmethod
    async def find_all_by_user(cls, session: AsyncSession, user_id: uuid.UUID) -> List[RuleModel]:
        stmt = cls._stmt(user_id).order_by(RuleModel.priority, RuleModel.id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def find_active_by_user(cls, session: AsyncSession, user_id: uuid.UUID) -> List[RuleModel]:
        stmt = cls._stmt(user_id).where(RuleModel.is_active.is_(True)).order_by(RuleModel.priority, RuleModel.id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def find_one_by_user(cls, session: AsyncSession, rule_id: int, user_id: uuid.UUID) -> Optional[RuleModel]:
        stmt = cls._stmt(user_id).where(RuleModel.id == rule_id)
        result = await session.execute(stmt)
        return result.scalars().one_or_none()


class RuleEngine:
    """Apply rules to already existing records."""

    @classmethod
    async def apply_to_existing(
        cls,
        user_id: uuid.UUID,
        start_date=None,
        end_date=None,
        dry_run: bool = False,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> RuleApplyResult:
        maker = session_maker or async_session_maker
        matched_rules: set = set()
        updated = 0
        async with maker() as session:
            rules = await RuleDAO.find_active_by_user(session, user_id)
            stmt = (
                select(TransactionModel)
                .join(TransactionModel.account)
                .where(TransactionModel.account.has(user_id=user_id))
                .order_by(TransactionModel.date)
            )
            if start_date is not None:
                stmt = stmt.where(TransactionModel.date >= start_date)
            if end_date is not None:
                stmt = stmt.where(TransactionModel.date <= end_date)
            result = await session.execute(stmt)
            transactions = list(result.scalars().unique().all())

            for transaction in transactions:
                before = (
                    transaction.category_id,
                    transaction.is_excluded,
                    frozenset(await tag_ids_of(session, transaction.id)),
                )
                matched = await apply_rules(session, transaction, user_id, rules=rules)
                after = (
                    transaction.category_id,
                    transaction.is_excluded,
                    frozenset(await tag_ids_of(session, transaction.id)),
                )
                matched_rules.update(matched)
                if matched and after != before:
                    updated += 1

            if dry_run:
                await session.rollback()
            else:
                await session.commit()
        return RuleApplyResult(
            matched_rules=sorted(matched_rules),
            updated_transactions=updated,
            dry_run=dry_run,
        )


class RuleService:
    """Rule CRUD and running the engine."""

    dao = RuleDAO

    @classmethod
    async def get_list_by_user(
        cls, user_id: uuid.UUID, session_maker: Optional[async_sessionmaker] = None
    ) -> List[RuleResponse]:
        maker = session_maker or async_session_maker
        async with maker() as session:
            rules = await cls.dao.find_all_by_user(session, user_id)
            return [await cls._to_response(session, rule) for rule in rules]

    @classmethod
    async def _to_response(cls, session: AsyncSession, rule: RuleModel) -> RuleResponse:
        category_name = None
        tag_name = None
        if rule.set_category_id is not None:
            category = await session.get(CategoryModel, rule.set_category_id)
            category_name = category.name if category else None
        if rule.add_tag_id is not None:
            tag = await session.get(TagModel, rule.add_tag_id)
            tag_name = tag.name if tag else None
        return RuleResponse(
            id=rule.id,
            name=rule.name,
            is_active=rule.is_active,
            priority=rule.priority,
            field=rule.field,
            operator=rule.operator,
            value=rule.value,
            set_category_id=rule.set_category_id,
            add_tag_id=rule.add_tag_id,
            exclude_from_statistics=rule.exclude_from_statistics,
            category_name=category_name,
            tag_name=tag_name,
        )

    @classmethod
    async def create_for_user(
        cls,
        schema: RuleCreate,
        user_id: uuid.UUID,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> RuleResponse:
        maker = session_maker or async_session_maker
        async with maker() as session:
            await cls._validate_links(session, schema.set_category_id, schema.add_tag_id, user_id)
            rule = RuleModel(user_id=user_id, **schema.model_dump())
            session.add(rule)
            await session.commit()
            await session.refresh(rule)
            return await cls._to_response(session, rule)

    @classmethod
    async def get_by_user(
        cls,
        rule_id: int,
        user_id: uuid.UUID,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> RuleResponse:
        maker = session_maker or async_session_maker
        async with maker() as session:
            rule = await cls.dao.find_one_by_user(session, rule_id, user_id)
            if rule is None:
                raise _not_found()
            return await cls._to_response(session, rule)

    @classmethod
    async def update_for_user(
        cls,
        rule_id: int,
        schema: RuleUpdate,
        user_id: uuid.UUID,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> RuleResponse:
        maker = session_maker or async_session_maker
        async with maker() as session:
            rule = await cls.dao.find_one_by_user(session, rule_id, user_id)
            if rule is None:
                raise _not_found()
            data = schema.model_dump(exclude_unset=True)
            await cls._validate_links(
                session,
                data.get("set_category_id", rule.set_category_id),
                data.get("add_tag_id", rule.add_tag_id),
                user_id,
            )
            for field, value in data.items():
                setattr(rule, field, value)
            await session.commit()
            await session.refresh(rule)
            return await cls._to_response(session, rule)

    @classmethod
    async def delete_for_user(
        cls,
        rule_id: int,
        user_id: uuid.UUID,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> None:
        maker = session_maker or async_session_maker
        async with maker() as session:
            rule = await cls.dao.find_one_by_user(session, rule_id, user_id)
            if rule is None:
                raise _not_found()
            await session.delete(rule)
            await session.commit()

    @classmethod
    async def _validate_links(
        cls,
        session: AsyncSession,
        category_id: Optional[int],
        tag_id: Optional[int],
        user_id: uuid.UUID,
    ) -> None:
        if category_id is not None:
            category = await session.get(CategoryModel, category_id)
            if category is None or category.user_id != user_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown category")
        if tag_id is not None:
            tag = await session.get(TagModel, tag_id)
            if tag is None or tag.user_id != user_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown tag")

    @classmethod
    async def apply_to_existing(
        cls,
        user_id: uuid.UUID,
        start_date=None,
        end_date=None,
        dry_run: bool = False,
        session_maker: Optional[async_sessionmaker] = None,
    ) -> RuleApplyResult:
        return await RuleEngine.apply_to_existing(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            dry_run=dry_run,
            session_maker=session_maker,
        )


class RuleViewSet(BaseViewSet[int, RuleCreate, RuleUpdate]):
    permission = FinancePermission
    service = RuleService

    @classmethod
    @check_permissions(action="list_rules")
    async def list(
        cls,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> List[RuleResponse]:
        return await cls.service.get_list_by_user(user_id=user.id, session_maker=session_maker)

    @classmethod
    @check_permissions(action="retrieve_rule")
    async def retrieve(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> RuleResponse:
        return await cls.service.get_by_user(rule_id=obj_id, user_id=user.id, session_maker=session_maker)

    @classmethod
    @check_permissions(action="create_rule")
    async def create(
        cls,
        obj_data: RuleCreate,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> RuleResponse:
        return await cls.service.create_for_user(schema=obj_data, user_id=user.id, session_maker=session_maker)

    @classmethod
    @check_permissions(action="update_rule")
    async def update(
        cls,
        obj_id: int,
        obj_data: RuleUpdate,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> RuleResponse:
        return await cls.service.update_for_user(
            rule_id=obj_id,
            schema=obj_data,
            user_id=user.id,
            session_maker=session_maker,
        )

    @classmethod
    @check_permissions(action="delete_rule")
    async def delete(
        cls,
        obj_id: int,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> None:
        await cls.service.delete_for_user(rule_id=obj_id, user_id=user.id, session_maker=session_maker)

    @classmethod
    @check_permissions(action="apply_rules")
    async def apply(
        cls,
        user: User,
        start_date=None,
        end_date=None,
        dry_run: bool = False,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> RuleApplyResult:
        return await cls.service.apply_to_existing(
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            dry_run=dry_run,
            session_maker=session_maker,
        )


rules_router = APIRouter(prefix="/api/finance/rules", tags=["Rules"])


@rules_router.get("/", status_code=status.HTTP_200_OK, response_model=List[RuleResponse])
async def list_rules(
    request: Request,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[RuleResponse]:
    """Auto-categorization rules in priority order."""
    return await RuleViewSet.list(request=request, user=user, session_maker=session_maker)


@rules_router.post("/", status_code=status.HTTP_201_CREATED, response_model=RuleResponse)
async def create_rule(
    request: Request,
    user: CurrentUser,
    payload: RuleCreate,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> RuleResponse:
    """New rule; category and tag must belong to the user."""
    return await RuleViewSet.create(request=request, user=user, obj_data=payload, session_maker=session_maker)


@rules_router.post("/apply", status_code=status.HTTP_200_OK, response_model=RuleApplyResult)
async def apply_rules_endpoint(
    request: Request,
    user: CurrentUser,
    start_date: Optional[datetime] = Query(None, description="Start of the application period"),
    end_date: Optional[datetime] = Query(None, description="End of the application period"),
    dry_run: bool = Query(False, description="Only show what would change"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> RuleApplyResult:
    """Run rules over existing records (e.g. after creating a rule)."""
    return await RuleViewSet.apply(
        request=request,
        user=user,
        start_date=start_date,
        end_date=end_date,
        dry_run=dry_run,
        session_maker=session_maker,
    )


@rules_router.get("/{rule_id}", status_code=status.HTTP_200_OK, response_model=RuleResponse)
async def get_rule(
    request: Request,
    user: CurrentUser,
    rule_id: int,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> RuleResponse:
    """Rule by ID."""
    return await RuleViewSet.retrieve(request=request, user=user, obj_id=rule_id, session_maker=session_maker)


@rules_router.patch("/{rule_id}", status_code=status.HTTP_200_OK, response_model=RuleResponse)
async def update_rule(
    request: Request,
    user: CurrentUser,
    rule_id: int,
    payload: RuleUpdate,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> RuleResponse:
    """Update a rule."""
    return await RuleViewSet.update(
        request=request,
        user=user,
        obj_id=rule_id,
        obj_data=payload,
        session_maker=session_maker,
    )


@rules_router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    request: Request,
    user: CurrentUser,
    rule_id: int,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> None:
    """Delete a rule; already applied changes are not rolled back."""
    await RuleViewSet.delete(request=request, user=user, obj_id=rule_id, session_maker=session_maker)
