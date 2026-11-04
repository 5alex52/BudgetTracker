"""Quick-entry template tests."""

from datetime import datetime

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from src.finance.schemas import TagCreate
from src.finance.schemas import TemplateCreate
from src.finance.schemas import TemplateUpdate
from src.finance.schemas import TransactionType
from src.finance.service import AccountService
from src.finance.tags import TagService
from src.finance.templates import TemplateService

PERIOD_START = datetime(2025, 10, 1)


def _schema(account, category, **overrides) -> TemplateCreate:
    data = {
        "name": "Кофе",
        "type": TransactionType.EXPENSE,
        "amount": 3.5,
        "currency_id": account.currency_id,
        "account_id": account.id,
        "category_id": category.id,
        "note": "Кофе по утрам",
    }
    data.update(overrides)
    return TemplateCreate(**data)


@pytest.mark.asyncio
async def test_template_crud_through_api(verified_user_client, currencies):
    client, _, _ = verified_user_client
    account = (
        await client.post(
            "/api/finance/accounts/",
            json={
                "name": "Cash",
                "type": "cash",
                "currency_id": "USD",
                "balance": 100.0,
            },
        )
    ).json()
    category = (await client.post("/api/finance/categories/", json={"name": "Кафе", "type": "expense"})).json()

    created = await client.post(
        "/api/finance/templates/",
        json={
            "name": "Кофе",
            "type": "expense",
            "amount": 3.5,
            "currency_id": "USD",
            "account_id": account["id"],
            "category_id": category["id"],
        },
    )
    assert created.status_code == 201
    template_id = created.json()["id"]
    assert created.json()["usage_count"] == 0

    listed = await client.get("/api/finance/templates/")
    assert [item["name"] for item in listed.json()] == ["Кофе"]

    updated = await client.patch(f"/api/finance/templates/{template_id}", json={"amount": 4.0})
    assert updated.json()["amount"] == 4.0

    deleted = await client.delete(f"/api/finance/templates/{template_id}")
    assert deleted.status_code == 204
    assert (await client.get("/api/finance/templates/")).json() == []


@pytest.mark.asyncio
async def test_apply_template_creates_transaction_and_counts_usage(user, account, expense_category, session_maker):
    template = await TemplateService.create_for_user(
        schema=_schema(account, expense_category),
        user_id=user.id,
        session_maker=session_maker,
    )

    transaction = await TemplateService.apply(template.id, user.id, date=PERIOD_START, session_maker=session_maker)

    assert transaction.amount == 3.5
    assert transaction.category_id == expense_category.id
    assert transaction.note == "Кофе по утрам"

    refreshed = await AccountService.get_by_user(account.id, user.id, session_maker=session_maker)
    assert refreshed.balance == 996.5

    stored = await TemplateService.get_by_user(template.id, user.id, session_maker=session_maker)
    assert stored.usage_count == 1


@pytest.mark.asyncio
async def test_apply_template_copies_tags(user, account, expense_category, session_maker):
    tag = await TagService.create_for_user(schema=TagCreate(name="Утро"), user_id=user.id, session_maker=session_maker)
    template = await TemplateService.create_for_user(
        schema=_schema(account, expense_category, tag_ids=[tag.id]),
        user_id=user.id,
        session_maker=session_maker,
    )

    transaction = await TemplateService.apply(template.id, user.id, date=PERIOD_START, session_maker=session_maker)

    assert [item.id for item in transaction.tags] == [tag.id]


@pytest.mark.asyncio
async def test_template_rejects_foreign_account(user, other_user, account, session_maker):
    category = await _category(user, session_maker)

    with pytest.raises(HTTPException) as error:
        await TemplateService.create_for_user(
            schema=_schema(account, category),
            user_id=other_user.id,
            session_maker=session_maker,
        )

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_template_rejects_category_type_mismatch(user, account, income_category, session_maker):
    with pytest.raises(HTTPException) as error:
        await TemplateService.create_for_user(
            schema=_schema(account, income_category),
            user_id=user.id,
            session_maker=session_maker,
        )

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_template_is_isolated(user, other_user, account, expense_category, session_maker):
    template = await TemplateService.create_for_user(
        schema=_schema(account, expense_category),
        user_id=user.id,
        session_maker=session_maker,
    )

    assert await TemplateService.get_list_by_user(other_user.id, session_maker=session_maker) == []
    with pytest.raises(HTTPException) as error:
        await TemplateService.apply(template.id, other_user.id, session_maker=session_maker)
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_update_template_tags(user, account, expense_category, session_maker):
    first = await TagService.create_for_user(schema=TagCreate(name="Раз"), user_id=user.id, session_maker=session_maker)
    second = await TagService.create_for_user(
        schema=TagCreate(name="Два"), user_id=user.id, session_maker=session_maker
    )
    template = await TemplateService.create_for_user(
        schema=_schema(account, expense_category, tag_ids=[first.id]),
        user_id=user.id,
        session_maker=session_maker,
    )

    updated = await TemplateService.update_for_user(
        template.id,
        TemplateUpdate(tag_ids=[second.id]),
        user.id,
        session_maker=session_maker,
    )

    assert [tag.id for tag in updated.tags] == [second.id]


@pytest.mark.asyncio
async def test_templates_endpoints_require_authentication(async_client: AsyncClient):
    assert (await async_client.get("/api/finance/templates/")).status_code == 401


async def _category(user, session_maker):
    from src.finance.schemas import CategoryCreate
    from src.finance.schemas import CategoryType
    from src.finance.service import CategoryService

    return await CategoryService.create_for_user(
        schema=CategoryCreate(name="Кофе", type=CategoryType.EXPENSE),
        user_id=user.id,
        session_maker=session_maker,
    )
