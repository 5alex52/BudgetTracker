import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_finance_endpoints_require_authentication(async_client: AsyncClient):
    response = await async_client.get("/api/finance/accounts/")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_finance_flow(verified_user_client, currencies):
    async_client, _, _ = verified_user_client

    # Account
    response = await async_client.post(
        "/api/finance/accounts/",
        json={"name": "Cash", "type": "cash", "currency_id": "USD", "balance": 100.0},
    )
    assert response.status_code == 201
    account_id = response.json()["id"]
    assert response.json()["balance"] == 100.0

    # Category
    response = await async_client.post(
        "/api/finance/categories/",
        json={
            "name": "Groceries",
            "type": "expense",
            "color": "#ff0000",
            "icon": "cart",
        },
    )
    assert response.status_code == 201
    category_id = response.json()["id"]

    # Transaction changes the account balance
    response = await async_client.post(
        "/api/finance/transactions/",
        json={
            "account_id": account_id,
            "category_id": category_id,
            "amount": 40.0,
            "currency_id": "USD",
            "type": "expense",
            "date": "2024-05-15T12:00:00",
            "note": "Weekly shopping",
        },
    )
    assert response.status_code == 201
    transaction_id = response.json()["id"]

    response = await async_client.get(f"/api/finance/accounts/{account_id}")
    assert response.status_code == 200
    assert response.json()["balance"] == 60.0

    # Transaction list carries related objects
    response = await async_client.get("/api/finance/transactions/")
    assert response.status_code == 200
    transactions = response.json()
    assert len(transactions) == 1
    assert transactions[0]["account_name"] == "Cash"
    assert transactions[0]["category_name"] == "Groceries"
    assert transactions[0]["currency_symbol"] == "$"

    # Summary
    response = await async_client.get(
        "/api/finance/transactions/summary", params={"transaction_type": "expense"}
    )
    assert response.status_code == 200
    summary = response.json()
    assert summary["total"] == 40.0
    assert summary["transactions_count"] == 1
    assert summary["by_category"][0]["name"] == "Groceries"

    # Subscription on top of the transaction
    response = await async_client.post(
        "/api/finance/subscriptions/",
        json={
            "transaction_id": transaction_id,
            "frequency": "monthly",
            "next_payment_date": "2024-06-15T12:00:00",
        },
    )
    assert response.status_code == 201
    subscription_id = response.json()["id"]

    response = await async_client.get(
        "/api/finance/subscriptions/upcoming", params={"days": 7}
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Balance overview
    response = await async_client.get("/api/finance/accounts/balance")
    assert response.status_code == 200
    assert response.json()["total"] == 60.0

    # Dashboard of currencies is public
    response = await async_client.get("/api/finance/currencies/")
    assert response.status_code == 200
    assert {"USD", "EUR"} <= {currency["code"] for currency in response.json()}

    # Deletion restores the balance
    response = await async_client.delete(f"/api/finance/transactions/{transaction_id}")
    assert response.status_code == 204

    response = await async_client.get(f"/api/finance/accounts/{account_id}")
    assert response.json()["balance"] == 100.0

    response = await async_client.delete(
        f"/api/finance/subscriptions/{subscription_id}"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_currency_management_requires_superuser(verified_user_client, currencies):
    async_client, _, _ = verified_user_client

    response = await async_client.post(
        "/api/finance/currencies/",
        json={
            "code": "GBP",
            "name": "Pound Sterling",
            "symbol": "GBP",
            "exchange_rate_to_base": 1.25,
        },
    )

    assert response.status_code == 403
