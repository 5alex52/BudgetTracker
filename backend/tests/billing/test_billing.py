"""Billing tests: plans, subscriptions, payment methods, payments, and webhooks."""

import json

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from src.billing.dao import PlanDAO
from src.billing.models import PaymentStatus
from src.billing.providers import get_provider
from src.billing.service import BillingService


async def _seed_plans(session_maker) -> None:
    """Plans are created by migrations: in the test database we create them manually."""
    from src.billing.models import PlanModel
    from src.billing.models import PlanPeriod

    async with session_maker() as session:
        for code, name, price, period, features in (
            ("free", "Бесплатный", 0.0, PlanPeriod.NONE, ["1 счёт"]),
            ("monthly", "Месячный", 4.99, PlanPeriod.MONTH, ["аналитика"]),
            ("yearly", "Годовой", 49.99, PlanPeriod.YEAR, ["аналитика", "скидка"]),
        ):
            session.add(
                PlanModel(
                    code=code,
                    name=name,
                    price=price,
                    currency="USD",
                    period=period,
                    features=features,
                    sort_order=0,
                )
            )
        await session.commit()


@pytest.mark.asyncio
async def test_plans_are_public(verified_user_client, session_maker):
    async_client, _, _ = verified_user_client
    await _seed_plans(session_maker)

    response = await async_client.get("/api/billing/plans")

    assert response.status_code == 200
    codes = [plan["code"] for plan in response.json()]
    assert codes == ["free", "monthly", "yearly"]
    assert response.json()[1]["price"] == 4.99


@pytest.mark.asyncio
async def test_providers_expose_mock_as_default(async_client: AsyncClient):
    response = await async_client.get("/api/billing/providers")

    assert response.status_code == 200
    by_code = {item["code"]: item for item in response.json()}
    assert by_code["mock"]["is_mock"] is True
    assert by_code["mock"]["is_configured"] is True
    assert by_code["stripe"]["is_configured"] is False
    assert by_code["crypto"]["is_configured"] is False


@pytest.mark.asyncio
async def test_subscription_defaults_to_free_plan(verified_user_client):
    async_client, _, _ = verified_user_client

    response = await async_client.get("/api/billing/subscription")

    assert response.status_code == 200
    payload = response.json()
    assert payload["plan_code"] == "free"
    assert payload["status"] == "active"


@pytest.mark.asyncio
async def test_free_plan_does_not_create_payment(verified_user_client, session_maker):
    async_client, _, _ = verified_user_client
    await _seed_plans(session_maker)

    response = await async_client.post("/api/billing/subscription", json={"plan_code": "free"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "succeeded"
    assert payload["payment_id"] == 0
    assert payload["subscription"]["plan_code"] == "free"

    payments = await async_client.get("/api/billing/payments")
    assert payments.json() == []


@pytest.mark.asyncio
async def test_paid_plan_is_activated_by_mock_provider(verified_user_client, session_maker):
    async_client, _, _ = verified_user_client
    await _seed_plans(session_maker)

    response = await async_client.post("/api/billing/subscription", json={"plan_code": "monthly"})

    assert response.status_code == 200
    payload = response.json()
    # The mock confirms payment immediately — no redirect needed
    assert payload["requires_redirect"] is False
    assert payload["status"] == "succeeded"
    assert payload["provider"] == "mock"
    assert payload["subscription"]["plan_code"] == "monthly"
    assert payload["subscription"]["current_period_end"] is not None

    current = await async_client.get("/api/billing/subscription")
    assert current.json()["plan_code"] == "monthly"

    payments = await async_client.get("/api/billing/payments")
    assert len(payments.json()) == 1
    assert payments.json()[0]["status"] == "succeeded"
    assert payments.json()[0]["amount"] == 4.99


@pytest.mark.asyncio
async def test_unknown_plan_returns_404(verified_user_client, session_maker):
    async_client, _, _ = verified_user_client
    await _seed_plans(session_maker)

    response = await async_client.post("/api/billing/subscription", json={"plan_code": "platinum"})

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unconfigured_provider_does_not_grant_plan(verified_user_client, session_maker):
    """If the provider is not configured, the subscription is not activated — otherwise the plan would be granted for free."""
    async_client, _, _ = verified_user_client
    await _seed_plans(session_maker)

    response = await async_client.post("/api/billing/subscription", json={"plan_code": "monthly", "provider": "stripe"})

    assert response.status_code == 503
    subscription = await async_client.get("/api/billing/subscription")
    assert subscription.json()["plan_code"] == "free"

    payments = await async_client.get("/api/billing/payments")
    assert payments.json()[0]["status"] == "failed"


@pytest.mark.asyncio
async def test_cancel_subscription_at_period_end(verified_user_client, session_maker):
    async_client, _, _ = verified_user_client
    await _seed_plans(session_maker)
    await async_client.post("/api/billing/subscription", json={"plan_code": "monthly"})

    response = await async_client.request("DELETE", "/api/billing/subscription")

    assert response.status_code == 200
    payload = response.json()
    assert payload["cancel_at_period_end"] is True
    assert payload["status"] == "active"


@pytest.mark.asyncio
async def test_cancel_immediately(verified_user_client, session_maker):
    async_client, _, _ = verified_user_client
    await _seed_plans(session_maker)
    await async_client.post("/api/billing/subscription", json={"plan_code": "monthly"})

    response = await async_client.request("DELETE", "/api/billing/subscription", params={"immediately": True})

    assert response.status_code == 200
    assert response.json()["status"] == "canceled"


@pytest.mark.asyncio
async def test_cancel_without_subscription_returns_404(verified_user_client):
    async_client, _, _ = verified_user_client

    response = await async_client.request("DELETE", "/api/billing/subscription")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_payment_methods_lifecycle(verified_user_client):
    async_client, _, _ = verified_user_client

    created = await async_client.post("/api/billing/payment-methods", json={"kind": "card"})
    assert created.status_code == 201
    payload = created.json()
    assert payload["provider"] == "mock"
    assert payload["is_default"] is True
    assert payload["last4"] == "4242"

    second = await async_client.post("/api/billing/payment-methods", json={"make_default": False})
    assert second.status_code == 201
    assert second.json()["is_default"] is False

    listed = await async_client.get("/api/billing/payment-methods")
    assert len(listed.json()) == 2

    default = await async_client.post(f"/api/billing/payment-methods/{second.json()['id']}/default")
    assert default.json()["is_default"] is True

    listed = await async_client.get("/api/billing/payment-methods")
    defaults = [item["id"] for item in listed.json() if item["is_default"]]
    assert defaults == [second.json()["id"]]

    deleted = await async_client.delete(f"/api/billing/payment-methods/{payload['id']}")
    assert deleted.status_code == 204
    assert len((await async_client.get("/api/billing/payment-methods")).json()) == 1


@pytest.mark.asyncio
async def test_payment_methods_are_isolated(verified_user_client, other_user, session_maker):
    async_client, _, _ = verified_user_client
    created = await async_client.post("/api/billing/payment-methods", json={})

    # Another user cannot delete someone else's payment method
    with pytest.raises(HTTPException) as error:
        await BillingService.delete_payment_method(
            user_id=other_user.id,
            method_id=created.json()["id"],
            session_maker=session_maker,
        )
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_webhook_confirms_pending_payment(verified_user_client, session_maker):
    """Webhook is the real acquirer path; the mock can handle it too."""
    async_client, _, _ = verified_user_client
    await _seed_plans(session_maker)

    checkout = await async_client.post("/api/billing/subscription", json={"plan_code": "monthly"})
    reference = checkout.json()["provider_reference"]

    # Re-processing the same payment does not create a second subscription
    payload = json.dumps({"provider_reference": reference}).encode()
    response = await async_client.post(
        "/api/billing/webhooks/mock",
        content=payload,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"

    current = await async_client.get("/api/billing/subscription")
    assert current.json()["plan_code"] == "monthly"


@pytest.mark.asyncio
async def test_webhook_rejects_unknown_payment(verified_user_client, session_maker):
    async_client, _, _ = verified_user_client
    await _seed_plans(session_maker)

    payload = json.dumps({"provider_reference": "mock_missing"}).encode()
    response = await async_client.post(
        "/api/billing/webhooks/mock",
        content=payload,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_real_provider_rejects_unsigned_webhook(async_client: AsyncClient, session_maker):
    """A real provider requires a signature — otherwise the webhook is trivial to forge."""
    await _seed_plans(session_maker)

    payload = json.dumps({"provider_reference": "pi_123"}).encode()
    response = await async_client.post(
        "/api/billing/webhooks/stripe",
        content=payload,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_renaming_period_extends_existing_subscription(verified_user_client, session_maker):
    """Paying again for the same plan extends the period rather than creating a second subscription."""
    async_client, _, _ = verified_user_client
    await _seed_plans(session_maker)

    first = await async_client.post("/api/billing/subscription", json={"plan_code": "monthly"})
    second = await async_client.post("/api/billing/subscription", json={"plan_code": "monthly"})

    assert first.json()["subscription"]["id"] == second.json()["subscription"]["id"]
    assert second.json()["subscription"]["current_period_end"] > first.json()["subscription"]["current_period_end"]

    payments = await async_client.get("/api/billing/payments")
    assert len(payments.json()) == 2


@pytest.mark.asyncio
async def test_billing_endpoints_require_authentication(async_client: AsyncClient):
    for path in (
        "/api/billing/subscription",
        "/api/billing/payments",
        "/api/billing/payment-methods",
    ):
        response = await async_client.get(path)
        assert response.status_code == 401, f"{path} → {response.status_code}"


@pytest.mark.asyncio
async def test_mock_provider_always_approves():
    provider = get_provider("mock")
    checkout = await provider.create_checkout(
        user_id="user",
        amount=10.0,
        currency="USD",
        plan_code="monthly",
        return_url="http://localhost",
    )
    result = await provider.confirm(checkout.provider_reference)

    assert result.approved is True
    assert checkout.requires_redirect is False


@pytest.mark.asyncio
async def test_plan_dao_returns_active_plans_sorted(session_maker):
    await _seed_plans(session_maker)
    async with session_maker() as session:
        plans = await PlanDAO.find_all_active(session)

    assert [plan.code for plan in plans] == ["free", "monthly", "yearly"]
    assert all(isinstance(plan.features, list) for plan in plans)
    assert PaymentStatus.SUCCEEDED.value == "succeeded"
