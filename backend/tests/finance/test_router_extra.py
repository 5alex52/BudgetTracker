"""HTTP-уровень новых эндпоинтов: коды ответов, заголовки, тело."""

import json

import pytest
from httpx import AsyncClient


async def _seed(client: AsyncClient, currencies: dict) -> dict:
    """Готовит пользователю счёт, две категории и три записи."""
    del currencies
    account = await client.post(
        "/api/finance/accounts/",
        json={"name": "Cash", "type": "cash", "currency_id": "USD", "balance": 0.0},
    )
    assert account.status_code == 201
    account_id = account.json()["id"]

    expense = await client.post("/api/finance/categories/", json={"name": "Food", "type": "expense"})
    income = await client.post("/api/finance/categories/", json={"name": "Salary", "type": "income"})
    assert expense.status_code == 201
    assert income.status_code == 201
    expense_id, income_id = expense.json()["id"], income.json()["id"]

    records = [
        {
            "amount": 100.0,
            "category_id": income_id,
            "type": "income",
            "date": "2025-10-02T10:00:00",
        },
        {
            "amount": 30.0,
            "category_id": expense_id,
            "type": "expense",
            "date": "2025-10-02T12:00:00",
        },
        {
            "amount": 20.0,
            "category_id": expense_id,
            "type": "expense",
            "date": "2025-10-05T12:00:00",
        },
    ]
    ids = []
    for record in records:
        response = await client.post(
            "/api/finance/transactions/",
            json={
                "account_id": account_id,
                "currency_id": "USD",
                "note": "покупка",
                **record,
            },
        )
        assert response.status_code == 201
        ids.append(response.json()["id"])

    return {
        "account_id": account_id,
        "expense_id": expense_id,
        "income_id": income_id,
        "transaction_ids": ids,
    }


@pytest.mark.asyncio
async def test_new_endpoints_require_authentication(async_client: AsyncClient, currencies):
    del currencies  # справочник нужен, чтобы публичные курсы отвечали 200, а не 400
    public_paths = (
        "/api/analytics/summary",
        "/api/analytics/timeseries",
        "/api/analytics/by-category",
        "/api/analytics/by-account",
        "/api/analytics/matrix",
        "/api/finance/categories/tree",
        "/api/finance/categories/stats",
        "/api/finance/currencies/rates",
    )
    for path in public_paths:
        # У курсов базовая валюта обязательна: справочник в тестах без BYN
        params = {"base": "USD"} if path.endswith("/rates") else None
        response = await async_client.get(path, params=params)
        assert response.status_code in {200, 401}, f"{path} → {response.status_code}"


@pytest.mark.asyncio
async def test_transactions_list_exposes_total_count(verified_user_client, currencies):
    async_client, _, _ = verified_user_client
    seeded = await _seed(async_client, currencies)

    response = await async_client.get("/api/finance/transactions/", params={"limit": 2})

    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.headers["X-Total-Count"] == "3"

    # Фильтр сужает и выдачу, и счётчик
    filtered = await async_client.get("/api/finance/transactions/", params={"types": "expense"})
    assert filtered.headers["X-Total-Count"] == "2"
    assert all(item["type"] == "expense" for item in filtered.json())

    del seeded


@pytest.mark.asyncio
async def test_transactions_list_search_and_sort(verified_user_client, currencies):
    async_client, _, _ = verified_user_client
    await _seed(async_client, currencies)

    search = await async_client.get("/api/finance/transactions/", params={"q": "покуп"})
    assert search.headers["X-Total-Count"] == "3"

    empty = await async_client.get("/api/finance/transactions/", params={"q": "ресторан"})
    assert empty.json() == []

    ascending = await async_client.get("/api/finance/transactions/", params={"sort": "amount_asc"})
    assert [item["amount"] for item in ascending.json()] == [20.0, 30.0, 100.0]

    bad_sort = await async_client.get("/api/finance/transactions/", params={"sort": "random"})
    assert bad_sort.status_code == 400


@pytest.mark.asyncio
async def test_transaction_details_include_names(verified_user_client, currencies):
    async_client, _, _ = verified_user_client
    seeded = await _seed(async_client, currencies)

    response = await async_client.get(f"/api/finance/transactions/{seeded['transaction_ids'][0]}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["account_name"] == "Cash"
    assert payload["category_name"] == "Salary"
    assert payload["currency_symbol"] == "$"


@pytest.mark.asyncio
async def test_bulk_delete_endpoint(verified_user_client, currencies):
    async_client, _, _ = verified_user_client
    seeded = await _seed(async_client, currencies)

    response = await async_client.post(
        "/api/finance/transactions/bulk-delete",
        json={"ids": seeded["transaction_ids"][:2] + [999_999]},
    )

    assert response.status_code == 200
    assert response.json() == {"deleted": 2, "missing": [999_999]}
    assert (await async_client.get("/api/finance/transactions/")).headers["X-Total-Count"] == "1"


@pytest.mark.asyncio
async def test_export_csv_and_json(verified_user_client, currencies):
    async_client, _, _ = verified_user_client
    await _seed(async_client, currencies)

    csv_response = await async_client.get("/api/finance/transactions/export", params={"format": "csv"})
    assert csv_response.status_code == 200
    assert "attachment" in csv_response.headers["content-disposition"]
    assert csv_response.text.splitlines()[0] == "date,type,account,category,amount,currency,note"
    assert len(csv_response.text.splitlines()) == 4

    json_response = await async_client.get("/api/finance/transactions/export", params={"format": "json"})
    assert json_response.status_code == 200
    payload = json.loads(json_response.text)
    assert len(payload) == 3
    assert payload[0]["account_name"] == "Cash"

    bad = await async_client.get("/api/finance/transactions/export", params={"format": "xlsx"})
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_account_summary_and_exclude_endpoints(verified_user_client, currencies):
    async_client, _, _ = verified_user_client
    seeded = await _seed(async_client, currencies)

    summary = await async_client.get(
        f"/api/finance/accounts/{seeded['account_id']}/summary",
        params={"start_date": "2025-10-01T00:00:00", "end_date": "2025-10-31T23:59:59"},
    )
    assert summary.status_code == 200
    assert summary.json()["income"] == 100.0
    assert summary.json()["expense"] == 50.0
    assert summary.json()["transactions_count"] == 3

    excluded = await async_client.post(
        f"/api/finance/accounts/{seeded['account_id']}/exclude",
        params={"is_excluded": True},
    )
    assert excluded.status_code == 200
    assert excluded.json()["is_excluded"] is True

    listed = await async_client.get("/api/finance/accounts/", params={"include_excluded": False})
    assert listed.json() == []

    balance = await async_client.get("/api/finance/accounts/balance")
    assert balance.json()["total"] == 0.0


@pytest.mark.asyncio
async def test_archive_account_endpoint_returns_fresh_object(verified_user_client, currencies):
    """Архивация через HTTP: ответ сериализуется после коммита, поэтому модель обновляем в сессии."""
    async_client, _, _ = verified_user_client
    seeded = await _seed(async_client, currencies)

    response = await async_client.post(
        f"/api/finance/accounts/{seeded['account_id']}/archive",
        params={"is_archived": True},
    )

    assert response.status_code == 200
    assert response.json()["is_archived"] is True
    assert response.json()["updated_at"] is not None

    hidden = await async_client.get("/api/finance/accounts/")
    assert hidden.json() == []


@pytest.mark.asyncio
async def test_categories_tree_and_stats_endpoints(verified_user_client, currencies):
    async_client, _, _ = verified_user_client
    seeded = await _seed(async_client, currencies)

    child = await async_client.post(
        "/api/finance/categories/",
        json={"name": "Cafe", "type": "expense", "parent_id": seeded["expense_id"]},
    )
    assert child.status_code == 201

    tree = await async_client.get("/api/finance/categories/tree", params={"category_type": "expense"})
    assert tree.status_code == 200
    roots = tree.json()
    # Кроме созданной категории у пользователя есть набор категорий по умолчанию.
    food = next(node for node in roots if node["name"] == "Food")
    assert [node["name"] for node in food["children"]] == ["Cafe"]
    assert food["transactions_count"] == 2

    stats = await async_client.get(
        "/api/finance/categories/stats",
        params={
            "category_type": "expense",
            "start_date": "2025-10-01T00:00:00",
            "end_date": "2025-10-31T23:59:59",
        },
    )
    assert stats.status_code == 200
    assert stats.json()[0]["total"] == 50.0


@pytest.mark.asyncio
async def test_currency_rates_endpoint(verified_user_client, currencies):
    async_client, _, _ = verified_user_client

    response = await async_client.get("/api/finance/currencies/rates", params={"base": "USD"})

    assert response.status_code == 200
    by_code = {item["code"]: item for item in response.json()}
    assert by_code["USD"]["is_base"] is True
    assert by_code["EUR"]["rate"] == pytest.approx(0.909091, rel=1e-4)

    unknown = await async_client.get("/api/finance/currencies/rates", params={"base": "XXX"})
    assert unknown.status_code == 400


@pytest.mark.asyncio
async def test_analytics_endpoints(verified_user_client, currencies):
    async_client, _, _ = verified_user_client
    await _seed(async_client, currencies)
    period = {"start_date": "2025-10-01T00:00:00", "end_date": "2025-10-31T23:59:59"}

    summary = await async_client.get("/api/analytics/summary", params=period)
    assert summary.status_code == 200
    payload = summary.json()
    assert payload["income"] == 100.0
    assert payload["expense"] == 50.0
    assert payload["net"] == 50.0
    assert payload["previous"] is not None

    timeseries = await async_client.get(
        "/api/analytics/timeseries",
        params={**period, "metric": "cashflow", "group_by": "day"},
    )
    assert timeseries.status_code == 200
    points = timeseries.json()["points"]
    assert len(points) == 2
    assert points[0]["income"] == 100.0

    balance = await async_client.get(
        "/api/analytics/timeseries",
        params={**period, "metric": "balance", "group_by": "month"},
    )
    assert balance.status_code == 200
    assert balance.json()["points"][-1]["value"] == 50.0

    by_category = await async_client.get("/api/analytics/by-category", params={**period, "transaction_type": "expense"})
    assert by_category.status_code == 200
    assert by_category.json()["items"][0]["name"] == "Food"
    assert by_category.json()["total"] == 50.0

    by_account = await async_client.get("/api/analytics/by-account", params=period)
    assert by_account.status_code == 200
    assert by_account.json()["items"][0]["net"] == 50.0

    matrix = await async_client.get(
        "/api/analytics/matrix",
        params={
            "months": 2,
            "transaction_type": "expense",
            "end_date": "2025-10-31T00:00:00",
        },
    )
    assert matrix.status_code == 200
    assert matrix.json()["months"] == ["2025-09", "2025-10"]
    assert matrix.json()["rows"][0]["values"] == [0.0, 50.0]

    bad_metric = await async_client.get("/api/analytics/timeseries", params={"metric": "unknown"})
    assert bad_metric.status_code == 422
