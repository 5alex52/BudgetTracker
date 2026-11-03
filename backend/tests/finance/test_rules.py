"""Тесты правил авто-категоризации и движка применения."""

from datetime import datetime

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from src.finance.rules import match_rule
from src.finance.rules import RuleEngine
from src.finance.rules import RuleService
from src.finance.schemas import RuleCreate
from src.finance.schemas import RuleField
from src.finance.schemas import RuleOperator
from src.finance.schemas import RuleUpdate
from src.finance.schemas import TagCreate
from src.finance.schemas import TransactionCreate
from src.finance.schemas import TransactionType
from src.finance.schemas import TransactionUpdate
from src.finance.service import TransactionService
from src.finance.tags import TagService

PERIOD_START = datetime(2025, 10, 1)


class _FakeRule:
    """Минимальная заготовка правила для проверки чистого условия."""

    def __init__(self, field, operator, value):
        self.field = field
        self.operator = operator
        self.value = value


async def _tx(account, category, user, session_maker, amount=10.0, note=""):
    return await TransactionService.create_for_user(
        schema=TransactionCreate(
            account_id=account.id,
            category_id=category.id,
            amount=amount,
            currency_id=account.currency_id,
            type=TransactionType.EXPENSE,
            date=PERIOD_START,
            note=note,
        ),
        user_id=user.id,
        session_maker=session_maker,
    )


def test_match_rule_note_operators():
    contains = _FakeRule(RuleField.NOTE, RuleOperator.CONTAINS, "пятёрочка")
    equals = _FakeRule(RuleField.NOTE, RuleOperator.EQUALS, "такси")

    assert match_rule(contains, "Покупка в Пятёрочка", 10.0) is True
    assert match_rule(contains, "ВкусВилл", 10.0) is False
    assert match_rule(equals, "Такси", 10.0) is True
    assert match_rule(equals, "Такси домой", 10.0) is False
    # Числовые операторы к тексту не применяются
    assert (
        match_rule(_FakeRule(RuleField.NOTE, RuleOperator.GREATER, "5"), "что-то", 10.0)
        is False
    )


def test_match_rule_amount_operators():
    greater = _FakeRule(RuleField.AMOUNT, RuleOperator.GREATER, "100")
    less = _FakeRule(RuleField.AMOUNT, RuleOperator.LESS, "100")

    assert match_rule(greater, "", 100.5) is True
    assert match_rule(greater, "", 99.0) is False
    assert match_rule(less, "", 99.0) is True
    # Некорректное значение правила не срабатывает, а не падает
    assert (
        match_rule(
            _FakeRule(RuleField.AMOUNT, RuleOperator.GREATER, "дорого"), "", 10.0
        )
        is False
    )


@pytest.mark.asyncio
async def test_rule_sets_category_on_create(
    user, account, expense_category, income_category, session_maker
):
    groceries = await _category(user, session_maker, "Продукты")
    await RuleService.create_for_user(
        schema=RuleCreate(
            name="Пятёрочка → Продукты",
            field=RuleField.NOTE,
            operator=RuleOperator.CONTAINS,
            value="пятёрочка",
            set_category_id=groceries.id,
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    transaction = await _tx(
        account, expense_category, user, session_maker, note="Пятёрочка на углу"
    )

    assert transaction.category_id == groceries.id


@pytest.mark.asyncio
async def test_rule_adds_tag(user, account, expense_category, session_maker):
    tag = await TagService.create_for_user(
        schema=TagCreate(name="Продукты"), user_id=user.id, session_maker=session_maker
    )
    await RuleService.create_for_user(
        schema=RuleCreate(
            name="Добавить метку",
            field=RuleField.NOTE,
            operator=RuleOperator.CONTAINS,
            value="пятёрочка",
            add_tag_id=tag.id,
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    transaction = await _tx(
        account, expense_category, user, session_maker, note="Пятёрочка"
    )

    assert [item.id for item in transaction.tags] == [tag.id]


@pytest.mark.asyncio
async def test_rule_hides_transaction_from_statistics(
    user, account, expense_category, session_maker
):
    from src.analytics.service import AnalyticsService

    await RuleService.create_for_user(
        schema=RuleCreate(
            name="Крупные покупки не в статистике",
            field=RuleField.AMOUNT,
            operator=RuleOperator.GREATER,
            value="500",
            exclude_from_statistics=True,
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    await _tx(
        account, expense_category, user, session_maker, amount=1000.0, note="Диван"
    )
    await _tx(account, expense_category, user, session_maker, amount=100.0, note="Хлеб")

    summary = await AnalyticsService.summary(
        user_id=user.id,
        start_date=PERIOD_START,
        end_date=PERIOD_START.replace(hour=23),
        session_maker=session_maker,
    )
    assert summary.expense == 100.0

    # В списках запись остаётся: правило не удаляет данные
    listed = await TransactionService.get_list_by_user(
        user.id, session_maker=session_maker
    )
    assert len(listed) == 2
    assert [item.is_excluded for item in listed].count(True) == 1


@pytest.mark.asyncio
async def test_inactive_rule_is_ignored(user, account, expense_category, session_maker):
    groceries = await _category(user, session_maker, "Продукты")
    await RuleService.create_for_user(
        schema=RuleCreate(
            name="Выключенное правило",
            is_active=False,
            field=RuleField.NOTE,
            operator=RuleOperator.CONTAINS,
            value="пятёрочка",
            set_category_id=groceries.id,
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    transaction = await _tx(
        account, expense_category, user, session_maker, note="Пятёрочка"
    )

    assert transaction.category_id == expense_category.id


@pytest.mark.asyncio
async def test_priority_order_decides_winner(
    user, account, expense_category, session_maker
):
    first = await _category(user, session_maker, "Первая")
    second = await _category(user, session_maker, "Вторая")
    await RuleService.create_for_user(
        schema=RuleCreate(
            name="Приоритет 10",
            priority=10,
            field=RuleField.NOTE,
            operator=RuleOperator.CONTAINS,
            value="магазин",
            set_category_id=first.id,
        ),
        user_id=user.id,
        session_maker=session_maker,
    )
    await RuleService.create_for_user(
        schema=RuleCreate(
            name="Приоритет 20",
            priority=20,
            field=RuleField.NOTE,
            operator=RuleOperator.CONTAINS,
            value="магазин",
            set_category_id=second.id,
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    transaction = await _tx(
        account, expense_category, user, session_maker, note="Магазин у дома"
    )

    # Правило с меньшим приоритетом применяется раньше, последнее слово — за ним по порядку
    assert transaction.category_id == second.id


@pytest.mark.asyncio
async def test_rules_apply_to_existing_transactions(
    user, account, expense_category, session_maker
):
    already = await _tx(
        account, expense_category, user, session_maker, note="Пятёрочка"
    )
    groceries = await _category(user, session_maker, "Продукты")
    rule = await RuleService.create_for_user(
        schema=RuleCreate(
            name="Старые записи",
            field=RuleField.NOTE,
            operator=RuleOperator.CONTAINS,
            value="пятёрочка",
            set_category_id=groceries.id,
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    result = await RuleService.apply_to_existing(user.id, session_maker=session_maker)

    assert result.updated_transactions == 1
    assert result.matched_rules == [rule.id]
    updated = await TransactionService.get_by_user(
        already.id, user.id, session_maker=session_maker
    )
    assert updated.category_id == groceries.id


@pytest.mark.asyncio
async def test_dry_run_does_not_change_data(
    user, account, expense_category, session_maker
):
    already = await _tx(
        account, expense_category, user, session_maker, note="Пятёрочка"
    )
    groceries = await _category(user, session_maker, "Продукты")
    await RuleService.create_for_user(
        schema=RuleCreate(
            name="Черновик",
            field=RuleField.NOTE,
            operator=RuleOperator.CONTAINS,
            value="пятёрочка",
            set_category_id=groceries.id,
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    result = await RuleService.apply_to_existing(
        user.id, dry_run=True, session_maker=session_maker
    )

    assert result.dry_run is True
    assert result.updated_transactions == 1
    untouched = await TransactionService.get_by_user(
        already.id, user.id, session_maker=session_maker
    )
    assert untouched.category_id == expense_category.id


@pytest.mark.asyncio
async def test_rule_apply_endpoint(verified_user_client, currencies):
    client, _, _ = verified_user_client
    account = (
        await client.post(
            "/api/finance/accounts/",
            json={"name": "Cash", "type": "cash", "currency_id": "USD", "balance": 0.0},
        )
    ).json()
    expense = (
        await client.post(
            "/api/finance/categories/", json={"name": "Прочее", "type": "expense"}
        )
    ).json()
    groceries = (
        await client.post(
            "/api/finance/categories/", json={"name": "Продукты", "type": "expense"}
        )
    ).json()
    await client.post(
        "/api/finance/transactions/",
        json={
            "account_id": account["id"],
            "category_id": expense["id"],
            "amount": 25.0,
            "currency_id": "USD",
            "type": "expense",
            "date": "2025-10-01T10:00:00",
            "note": "Пятёрочка",
        },
    )
    await client.post(
        "/api/finance/rules/",
        json={
            "name": "Пятёрочка",
            "field": "note",
            "operator": "contains",
            "value": "пятёрочка",
            "set_category_id": groceries["id"],
        },
    )

    response = await client.post("/api/finance/rules/apply")

    assert response.status_code == 200
    assert response.json()["updated_transactions"] == 1
    listed = await client.get("/api/finance/transactions/")
    assert listed.json()[0]["category_name"] == "Продукты"


@pytest.mark.asyncio
async def test_rule_crud_through_api(verified_user_client):
    client, _, _ = verified_user_client

    created = await client.post(
        "/api/finance/rules/",
        json={
            "name": "Мелкие траты",
            "field": "amount",
            "operator": "less",
            "value": "5",
        },
    )
    assert created.status_code == 201
    rule_id = created.json()["id"]

    listed = await client.get("/api/finance/rules/")
    assert [item["id"] for item in listed.json()] == [rule_id]

    updated = await client.patch(
        f"/api/finance/rules/{rule_id}", json={"is_active": False}
    )
    assert updated.json()["is_active"] is False

    deleted = await client.delete(f"/api/finance/rules/{rule_id}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_rule_validates_foreign_category(user, other_user, session_maker):
    foreign_category = await _category(other_user, session_maker, "Чужая")

    with pytest.raises(HTTPException) as error:
        await RuleService.create_for_user(
            schema=RuleCreate(
                name="Чужая категория",
                field=RuleField.NOTE,
                operator=RuleOperator.CONTAINS,
                value="x",
                set_category_id=foreign_category.id,
            ),
            user_id=user.id,
            session_maker=session_maker,
        )

    assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_rules_are_isolated(
    user, other_user, account, expense_category, session_maker
):
    rule = await RuleService.create_for_user(
        schema=RuleCreate(
            name="Своё", field=RuleField.NOTE, operator=RuleOperator.CONTAINS, value="x"
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    assert (
        await RuleService.get_list_by_user(other_user.id, session_maker=session_maker)
        == []
    )
    with pytest.raises(HTTPException) as error:
        await RuleService.get_by_user(
            rule.id, other_user.id, session_maker=session_maker
        )
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_engine_counts_only_changed_transactions(
    user, account, expense_category, session_maker
):
    """Записи без совпадений не считаются изменёнными."""
    await _tx(account, expense_category, user, session_maker, note="ВкусВилл")
    await RuleService.create_for_user(
        schema=RuleCreate(
            name="Пятёрочка",
            field=RuleField.NOTE,
            operator=RuleOperator.CONTAINS,
            value="пятёрочка",
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    result = await RuleEngine.apply_to_existing(user.id, session_maker=session_maker)

    assert result.updated_transactions == 0
    assert result.matched_rules == []


@pytest.mark.asyncio
async def test_rules_endpoints_require_authentication(async_client: AsyncClient):
    assert (await async_client.get("/api/finance/rules/")).status_code == 401
    assert (await async_client.post("/api/finance/rules/apply")).status_code == 401


@pytest.mark.asyncio
async def test_update_rule_keeps_links(
    user, other_user, account, expense_category, session_maker
):
    tag = await TagService.create_for_user(
        schema=TagCreate(name="Метка"), user_id=user.id, session_maker=session_maker
    )
    rule = await RuleService.create_for_user(
        schema=RuleCreate(
            name="С меткой",
            field=RuleField.NOTE,
            operator=RuleOperator.CONTAINS,
            value="x",
            add_tag_id=tag.id,
        ),
        user_id=user.id,
        session_maker=session_maker,
    )

    updated = await RuleService.update_for_user(
        rule.id, RuleUpdate(priority=5), user.id, session_maker=session_maker
    )

    assert updated.priority == 5
    assert updated.tag_name == "Метка"
    del other_user, account, expense_category


async def _category(user, session_maker, name: str):
    from src.finance.schemas import CategoryCreate
    from src.finance.schemas import CategoryType
    from src.finance.service import CategoryService

    return await CategoryService.create_for_user(
        schema=CategoryCreate(name=name, type=CategoryType.EXPENSE),
        user_id=user.id,
        session_maker=session_maker,
    )
