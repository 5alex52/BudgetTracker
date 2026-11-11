"""Tests for the crypto wallet tracker: validation, ownership, manual mode, math."""

from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from src.crypto.adapters import parse_tronscan_account
from src.crypto.models import CryptoBalanceSnapshotModel
from src.crypto.models import CryptoHoldingModel
from src.crypto.models import CryptoPriceDailyModel
from src.crypto.models import CryptoSyncRunModel
from src.crypto.schemas import AddressIn
from src.crypto.schemas import Chain
from src.crypto.schemas import HoldingIn
from src.crypto.schemas import SnapshotSource
from src.crypto.schemas import WalletCreate
from src.crypto.schemas import WalletKind
from src.crypto.schemas import WalletUpdate
from src.crypto.service import CryptoService
from src.crypto.service import run_wallet_sync

EVM = "0x" + "a" * 40
BTC = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
TON = "UQ" + "A" * 46
TRON = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"


# --- address validation (trust boundary) ------------------------------------


@pytest.mark.parametrize(
    "chain,address",
    [
        ("evm", "0x123"),
        ("evm", "0x" + "g" * 40),
        ("btc", "1short"),
        ("btc", "bc1q" + " "),
        ("ton", "QQ" + "A" * 46),
        ("tron", "X" + "0" * 33),
        ("tron", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6"),  # 33 chars: one short
    ],
)
@pytest.mark.asyncio
async def test_invalid_addresses_rejected(verified_user_client, chain, address):
    client, _, _ = verified_user_client
    response = await client.post(
        "/api/crypto/wallets",
        json={"name": "W", "kind": "trust", "addresses": [{"chain": chain, "address": address}]},
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "chain,address",
    [("evm", EVM), ("btc", BTC), ("ton", TON), ("tron", TRON)],
)
@pytest.mark.asyncio
async def test_valid_addresses_accepted(verified_user_client, currencies, chain, address):
    client, _, _ = verified_user_client
    response = await client.post(
        "/api/crypto/wallets",
        json={"name": "Watch", "kind": "trust", "addresses": [{"chain": chain, "address": address}]},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["kind"] == "trust"
    assert body["addresses"] == [
        {"id": body["addresses"][0]["id"], "chain": chain, "address": address, "is_active": True}
    ]
    assert body["holdings"] == []
    assert body["total_base"] == 0.0


@pytest.mark.asyncio
async def test_duplicate_address_rejected(verified_user_client, currencies):
    client, _, _ = verified_user_client
    response = await client.post(
        "/api/crypto/wallets",
        json={
            "name": "W",
            "kind": "trust",
            "addresses": [{"chain": "evm", "address": EVM}, {"chain": "evm", "address": EVM}],
        },
    )
    assert response.status_code == 400


# --- ownership ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_wallets_are_isolated_per_user(user, other_user, currencies, session_maker):
    created = await CryptoService.create_for_user(WalletCreate(name="W", kind=WalletKind.TRUST), user.id, session_maker)
    with pytest.raises(HTTPException) as error:
        await CryptoService.update_for_user(created.id, WalletUpdate(name="X"), other_user.id, session_maker)
    assert error.value.status_code == 404
    with pytest.raises(HTTPException) as error:
        await CryptoService.balances(created.id, other_user.id, session_maker)
    assert error.value.status_code == 404
    with pytest.raises(HTTPException) as error:
        await CryptoService.delete_for_user(created.id, other_user.id, session_maker)
    assert error.value.status_code == 404


# --- manual wallets ----------------------------------------------------------


@pytest.mark.asyncio
async def test_manual_wallet_balances_flow(verified_user_client, currencies, session_maker):
    client, user_id, _ = verified_user_client
    today = date.today()
    async with session_maker() as session:
        session.add(CryptoPriceDailyModel(asset_code="BTC", day=today, price_usd=Decimal("60000")))
        await session.commit()

    response = await client.post(
        "/api/crypto/wallets",
        json={"name": "Ledger", "kind": "manual", "holdings": [{"asset_code": "BTC", "amount": 2}]},
    )
    assert response.status_code == 201
    wallet_id = response.json()["id"]

    response = await client.put(
        f"/api/crypto/wallets/{wallet_id}/balances",
        json={"holdings": [{"asset_code": "BTC", "amount": 3}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] is None
    assert body["holdings"][0]["asset_code"] == "BTC"
    assert body["holdings"][0]["amount"] == 3.0
    assert body["holdings"][0]["price_usd"] == 60000.0
    assert body["holdings"][0]["value_usd"] == 180000.0
    assert body["holdings"][0]["value_base"] == 180000.0
    assert body["total_usd"] == 180000.0

    async with session_maker() as session:
        snapshot = (
            (
                await session.execute(
                    select(CryptoBalanceSnapshotModel).where(
                        CryptoBalanceSnapshotModel.wallet_id == wallet_id,
                        CryptoBalanceSnapshotModel.asset_code == "BTC",
                        CryptoBalanceSnapshotModel.day == today,
                    )
                )
            )
            .scalars()
            .one()
        )
        assert float(snapshot.amount) == 3.0
        assert snapshot.source == SnapshotSource.MANUAL

    # hand-entered balances are for manual wallets only
    response = await client.post("/api/crypto/wallets", json={"name": "W", "kind": "trust"})
    trust_id = response.json()["id"]
    response = await client.put(
        f"/api/crypto/wallets/{trust_id}/balances", json={"holdings": [{"asset_code": "BTC", "amount": 1}]}
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_assets_endpoint_lists_distinct_codes(verified_user_client, currencies):
    client, _, _ = verified_user_client
    response = await client.post(
        "/api/crypto/wallets",
        json={"name": "W", "kind": "manual", "holdings": [{"asset_code": "BTC", "amount": 1}]},
    )
    assert response.status_code == 201
    response = await client.get("/api/crypto/assets")
    assert response.status_code == 200
    assert response.json() == {"assets": ["BTC"]}


# --- overview and timeseries math --------------------------------------------


@pytest.mark.asyncio
async def test_overview_and_timeseries_math(user, currencies, session_maker):
    today = date.today()
    yesterday = today - timedelta(days=1)
    async with session_maker() as session:
        session.add_all(
            [
                CryptoPriceDailyModel(asset_code="BTC", day=yesterday, price_usd=Decimal("50000")),
                CryptoPriceDailyModel(asset_code="BTC", day=today, price_usd=Decimal("60000")),
            ]
        )
        await session.commit()
    # Prices are seeded before holdings exist so no CoinGecko fetch is triggered
    wallet = await CryptoService.create_for_user(
        WalletCreate(name="W", kind=WalletKind.MANUAL, holdings=[HoldingIn(asset_code="BTC", amount=2)]),
        user.id,
        session_maker,
    )
    async with session_maker() as session:
        session.add_all(
            [
                CryptoBalanceSnapshotModel(
                    wallet_id=wallet.id,
                    asset_code="BTC",
                    day=yesterday,
                    amount=Decimal("1"),
                    price_usd=Decimal("50000"),
                    source=SnapshotSource.MANUAL,
                    taken_at=datetime.now(),
                ),
                # today's snapshot is written by create_for_user (amount 2, seeded price 60000)
            ]
        )
        await session.commit()

    # "all" starts at the earliest snapshot (yesterday): start value 1 BTC × 50000
    overview = await CryptoService.overview(user.id, "all", session_maker)
    assert overview.base_currency == "USD"
    assert overview.total_now_base == pytest.approx(120000.0)
    assert overview.change_absolute == pytest.approx(70000.0)
    assert overview.change_percent == pytest.approx(140.0)
    asset = overview.by_asset[0]
    assert asset.asset_code == "BTC"
    assert asset.amount == pytest.approx(2.0)
    assert asset.price_usd == pytest.approx(60000.0)
    assert asset.value_base == pytest.approx(120000.0)
    assert asset.change_percent == pytest.approx(140.0)
    assert overview.by_wallet[0].wallet_id == wallet.id
    assert overview.by_wallet[0].value_base == pytest.approx(120000.0)

    series = await CryptoService.timeseries(user.id, "7d", "total", session_maker)
    assert len(series["points"]) == 7
    points = {point["day"]: point for point in series["points"]}
    # 0 before the first snapshot, then the carried amounts priced per day
    for point in series["points"][:5]:
        assert point["total_base"] == 0.0
    assert points[yesterday]["total_base"] == pytest.approx(50000.0)
    assert points[yesterday]["by_asset"] == {"BTC": 50000.0}
    assert points[yesterday]["by_wallet"] == {str(wallet.id): 50000.0}
    assert points[today]["total_base"] == pytest.approx(120000.0)
    assert points[today]["by_asset"] == {"BTC": 120000.0}
    assert points[today]["by_wallet"] == {str(wallet.id): 120000.0}


@pytest.mark.asyncio
async def test_overview_without_any_data(user, currencies, session_maker):
    overview = await CryptoService.overview(user.id, "7d", session_maker)
    assert overview.total_now_base == 0.0
    assert overview.change_absolute == 0.0
    assert overview.change_percent is None
    assert overview.by_asset == []
    assert overview.by_wallet == []


# --- backfill / sync with mocked adapters ------------------------------------


@pytest.mark.asyncio
async def test_backfill_writes_holdings_snapshots_and_sync_run(user, currencies, session_maker, monkeypatch):
    async def fake_fetch_holdings(chain, address):
        return [("BTC", Decimal("1.5"))]

    async def fake_fetch_daily_history(chain, address, days=365):
        today = date.today()
        return {today - timedelta(days=1): {"BTC": Decimal("1")}, today: {"BTC": Decimal("1.5")}}

    async def fake_fetch_daily(asset, start_day, end_day):
        return {start_day + timedelta(days=index): Decimal("55000") for index in range((end_day - start_day).days + 1)}

    monkeypatch.setattr("src.crypto.adapters.fetch_holdings", fake_fetch_holdings)
    monkeypatch.setattr("src.crypto.adapters.fetch_daily_history", fake_fetch_daily_history)
    monkeypatch.setattr("src.crypto.prices.fetch_daily", fake_fetch_daily)

    wallet = await CryptoService.create_for_user(
        WalletCreate(name="W", kind=WalletKind.TRUST, addresses=[AddressIn(chain=Chain.EVM, address=EVM)]),
        user.id,
        session_maker,
    )
    sync_status = await run_wallet_sync(wallet.id, session_maker, SnapshotSource.BACKFILL, include_history=True)
    assert sync_status == "ok"

    today = date.today()
    async with session_maker() as session:
        holding = (
            (
                await session.execute(
                    select(CryptoHoldingModel).where(
                        CryptoHoldingModel.wallet_id == wallet.id,
                        CryptoHoldingModel.asset_code == "BTC",
                    )
                )
            )
            .scalars()
            .one()
        )
        assert float(holding.amount) == 1.5
        snapshots = (
            (
                await session.execute(
                    select(CryptoBalanceSnapshotModel)
                    .where(CryptoBalanceSnapshotModel.wallet_id == wallet.id)
                    .order_by(CryptoBalanceSnapshotModel.day)
                )
            )
            .scalars()
            .all()
        )
        assert {row.day: float(row.amount) for row in snapshots} == {
            today - timedelta(days=1): 1.0,
            today: 1.5,
        }
        assert {row.source for row in snapshots} == {SnapshotSource.BACKFILL}
        sync_run = (
            (await session.execute(select(CryptoSyncRunModel).where(CryptoSyncRunModel.wallet_id == wallet.id)))
            .scalars()
            .one()
        )
        assert sync_run.status == "ok"
        assert sync_run.error is None
        assert sync_run.finished_at is not None


@pytest.mark.asyncio
async def test_sync_error_is_recorded(user, currencies, session_maker, monkeypatch):
    from src.crypto import adapters

    async def failing_fetch(chain, address):
        raise adapters.SyncError("rpc down")

    async def no_history(asset, start_day, end_day):
        return {}

    monkeypatch.setattr("src.crypto.adapters.fetch_holdings", failing_fetch)
    monkeypatch.setattr("src.crypto.prices.fetch_daily", no_history)
    wallet = await CryptoService.create_for_user(
        WalletCreate(name="W", kind=WalletKind.TRUST, addresses=[AddressIn(chain=Chain.EVM, address=EVM)]),
        user.id,
        session_maker,
    )
    sync_status = await run_wallet_sync(wallet.id, session_maker, SnapshotSource.SCHEDULER)
    assert sync_status == "error"
    async with session_maker() as session:
        sync_run = (
            (await session.execute(select(CryptoSyncRunModel).where(CryptoSyncRunModel.wallet_id == wallet.id)))
            .scalars()
            .one()
        )
        assert sync_run.status == "error"
        assert "rpc down" in sync_run.error


@pytest.mark.asyncio
async def test_scheduler_snapshots_manual_wallet_without_network(user, currencies, session_maker, monkeypatch):
    async def no_history(asset, start_day, end_day):
        return {}

    monkeypatch.setattr("src.crypto.prices.fetch_daily", no_history)
    wallet = await CryptoService.create_for_user(
        WalletCreate(name="W", kind=WalletKind.MANUAL, holdings=[HoldingIn(asset_code="BTC", amount=2)]),
        user.id,
        session_maker,
    )
    sync_status = await run_wallet_sync(wallet.id, session_maker, SnapshotSource.SCHEDULER)
    assert sync_status == "ok"
    async with session_maker() as session:
        snapshot = (
            (
                await session.execute(
                    select(CryptoBalanceSnapshotModel).where(
                        CryptoBalanceSnapshotModel.wallet_id == wallet.id,
                        CryptoBalanceSnapshotModel.day == date.today(),
                    )
                )
            )
            .scalars()
            .one()
        )
        assert float(snapshot.amount) == 2.0
        assert snapshot.source == SnapshotSource.MANUAL


# --- TRON adapter parsing (pure function) ------------------------------------


def test_parse_tronscan_account():
    payload = {
        "balance": "15000000",  # 15 TRX in sun
        "tokenBalances": [
            {"tokenType": "trc20", "tokenAbbr": "USDT", "tokenDecimal": 6, "balance": "12345678"},
            {"tokenType": "trx", "tokenAbbr": "TRX", "tokenDecimal": 6, "balance": "1000000"},
            {"tokenType": "trc20", "tokenAbbr": "JST", "tokenDecimal": 6, "balance": "0"},
        ],
    }
    holdings = dict(parse_tronscan_account(payload))
    assert holdings == {"TRX": Decimal("15"), "USDT": Decimal("12.345678")}


def test_parse_tronscan_account_empty():
    assert parse_tronscan_account({}) == []
