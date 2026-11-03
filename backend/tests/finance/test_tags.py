"""Тесты меток: CRUD, счётчики и связь с записями."""

from datetime import datetime

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from src.finance.schemas import TagCreate
from src.finance.schemas import TagUpdate
from src.finance.schemas import TransactionCreate
from src.finance.schemas import TransactionType
from src.finance.schemas import TransactionUpdate
from src.finance.service import TransactionService
from src.finance.tags import TagService

PERIOD_START = datetime(2025, 10, 1)


async def _tx(
    account,
    category,
    user,
    session_maker,
    amount=10.0,
    note="",
    tag_ids=None,
    kind=TransactionType.EXPENSE,
):
    return await TransactionService.create_for_user(
        schema=TransactionCreate(
            account_id=account.id,
            category_id=category.id,
            amount=amount,
            currency_id=account.currency_id,
            type=kind,
            date=PERIOD_START,
            note=note,
            tag_ids=tag_ids or [],
        ),
        user_id=user.id,
        session_maker=session_maker,
    )


@pytest.mark.asyncio
async def test_tag_crud_through_api(verified_user_client):
    client, _, _ = verified_user_client

    created = await client.post(
        "/api/finance/tags/", json={"name": "Отпуск", "color": "#ff0000"}
    )
    assert created.status_code == 201
    tag_id = created.json()["id"]
    assert created.json()["transactions_count"] == 0

    listed = await client.get("/api/finance/tags/")
    assert [tag["name"] for tag in listed.json()] == ["Отпуск"]

    updated = await client.patch(
        f"/api/finance/tags/{tag_id}", json={"name": "Отпуск 2025"}
    )
    assert updated.json()["name"] == "Отпуск 2025"

    deleted = await client.delete(f"/api/finance/tags/{tag_id}")
    assert deleted.status_code == 204
    assert (await client.get("/api/finance/tags/")).json() == []


@pytest.mark.asyncio
async def test_tag_name_is_unique_per_user(user, session_maker):
    await TagService.create_for_user(
        schema=TagCreate(name="Ремонт"), user_id=user.id, session_maker=session_maker
    )

    with pytest.raises(HTTPException) as error:
        await TagService.create_for_user(
            schema=TagCreate(name="Ремонт"),
            user_id=user.id,
            session_maker=session_maker,
        )

    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_same_tag_name_allowed_for_different_users(
    user, other_user, session_maker
):
    await TagService.create_for_user(
        schema=TagCreate(name="Работа"), user_id=user.id, session_maker=session_maker
    )
    tag = await TagService.create_for_user(
        schema=TagCreate(name="Работа"),
        user_id=other_user.id,
        session_maker=session_maker,
    )

    assert tag.name == "Работа"


@pytest.mark.asyncio
async def test_tags_are_isolated_between_users(user, other_user, session_maker):
    foreign = await TagService.create_for_user(
        schema=TagCreate(name="Чужая"),
        user_id=other_user.id,
        session_maker=session_maker,
    )

    assert await TagService.get_list_by_user(user.id, session_maker=session_maker) == []
    with pytest.raises(HTTPException) as error:
        await TagService.get_by_user(foreign.id, user.id, session_maker=session_maker)
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_transaction_keeps_tags(user, account, expense_category, session_maker):
    tag = await TagService.create_for_user(
        schema=TagCreate(name="Отпуск"), user_id=user.id, session_maker=session_maker
    )

    transaction = await _tx(
        account, expense_category, user, session_maker, tag_ids=[tag.id]
    )

    assert [item.id for item in transaction.tags] == [tag.id]
    stats = await TagService.get_list_by_user(user.id, session_maker=session_maker)
    assert stats[0].transactions_count == 1


@pytest.mark.asyncio
async def test_update_replaces_tags(user, account, expense_category, session_maker):
    first = await TagService.create_for_user(
        schema=TagCreate(name="Первый"), user_id=user.id, session_maker=session_maker
    )
    second = await TagService.create_for_user(
        schema=TagCreate(name="Второй"), user_id=user.id, session_maker=session_maker
    )
    transaction = await _tx(
        account, expense_category, user, session_maker, tag_ids=[first.id]
    )

    updated = await TransactionService.update_for_user(
        transaction_id=transaction.id,
        schema=TransactionUpdate(tag_ids=[second.id]),
        user_id=user.id,
        session_maker=session_maker,
    )
    assert [item.id for item in updated.tags] == [second.id]

    cleared = await TransactionService.update_for_user(
        transaction_id=transaction.id,
        schema=TransactionUpdate(tag_ids=[]),
        user_id=user.id,
        session_maker=session_maker,
    )
    assert cleared.tags == []


@pytest.mark.asyncio
async def test_foreign_tag_on_transaction_is_rejected(
    user, other_user, account, expense_category, session_maker
):
    foreign = await TagService.create_for_user(
        schema=TagCreate(name="Чужая"),
        user_id=other_user.id,
        session_maker=session_maker,
    )

    with pytest.raises(HTTPException) as error:
        await _tx(account, expense_category, user, session_maker, tag_ids=[foreign.id])

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_filter_transactions_by_tags(
    user, account, expense_category, session_maker
):
    work = await TagService.create_for_user(
        schema=TagCreate(name="Работа"), user_id=user.id, session_maker=session_maker
    )
    travel = await TagService.create_for_user(
        schema=TagCreate(name="Поездка"), user_id=user.id, session_maker=session_maker
    )
    await _tx(
        account, expense_category, user, session_maker, amount=10.0, tag_ids=[work.id]
    )
    await _tx(
        account, expense_category, user, session_maker, amount=20.0, tag_ids=[travel.id]
    )
    await _tx(
        account,
        expense_category,
        user,
        session_maker,
        amount=30.0,
        tag_ids=[work.id, travel.id],
    )

    by_work = await TransactionService.get_list_by_user(
        user.id, session_maker=session_maker, tag_ids=[work.id]
    )
    both = await TransactionService.get_list_by_user(
        user.id, session_maker=session_maker, tag_ids=[work.id, travel.id]
    )

    assert sorted(item.amount for item in by_work) == [10.0, 30.0]
    assert sorted(item.amount for item in both) == [10.0, 20.0, 30.0]


@pytest.mark.asyncio
async def test_deleting_tag_keeps_transactions(
    user, account, expense_category, session_maker
):
    tag = await TagService.create_for_user(
        schema=TagCreate(name="Временная"), user_id=user.id, session_maker=session_maker
    )
    transaction = await _tx(
        account, expense_category, user, session_maker, tag_ids=[tag.id]
    )

    await TagService.delete_for_user(tag.id, user.id, session_maker=session_maker)

    kept = await TransactionService.get_by_user(
        transaction.id, user.id, session_maker=session_maker
    )
    assert kept.id == transaction.id
    assert kept.tags == []


@pytest.mark.asyncio
async def test_tags_endpoints_require_authentication(async_client: AsyncClient):
    assert (await async_client.get("/api/finance/tags/")).status_code == 401
    assert (
        await async_client.post("/api/finance/tags/", json={"name": "x"})
    ).status_code == 401


@pytest.mark.asyncio
async def test_tag_count_grows_with_transactions(
    user, account, expense_category, session_maker
):
    tag = await TagService.create_for_user(
        schema=TagCreate(name="Частое"), user_id=user.id, session_maker=session_maker
    )
    await _tx(account, expense_category, user, session_maker, tag_ids=[tag.id])
    await _tx(account, expense_category, user, session_maker, tag_ids=[tag.id])

    # Название меняется — счётчик не теряется
    updated = await TagService.update_for_user(
        tag.id, TagUpdate(color="#00ff00"), user.id, session_maker=session_maker
    )
    assert updated.color == "#00ff00"

    stats = await TagService.get_list_by_user(user.id, session_maker=session_maker)
    assert stats[0].transactions_count == 2
