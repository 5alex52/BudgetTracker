"""Tests for the crypto wallet tracker: validation, ownership, manual mode, math."""

from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from src.crypto import service as crypto_service
from src.crypto.adapters import parse_avalanche_balances
from src.crypto.adapters import parse_solana_account
from src.crypto.adapters import parse_tronscan_account
from src.crypto.adapters import validate_address
from src.crypto.models import CryptoBalanceSnapshotModel
from src.crypto.models import CryptoHoldingModel
from src.crypto.models import CryptoPriceDailyModel
from src.crypto.models import CryptoSyncRunModel
from src.crypto.schemas import AddressIn
from src.crypto.schemas import Chain
from src.crypto.schemas import HoldingIn
from src.crypto.schemas import SnapshotSource
from src.crypto.schemas import SyncStatus
from src.crypto.schemas import WalletCreate
from src.crypto.schemas import WalletKind
from src.crypto.schemas import WalletUpdate
from src.crypto.service import CryptoService
from src.crypto.service import run_syncs_once
from src.crypto.service import run_wallet_sync
from src.finance.schemas import AccountType
from src.finance.schemas import AccountUpdate
from src.finance.schemas import TransactionCreate
from src.finance.schemas import TransactionType
from src.finance.service import AccountService
from src.finance.service import TransactionService

EVM = "0x" + "a" * 40
BTC = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
TON = "UQ" + "A" * 46
TRON = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
SOLANA = "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9"


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
        ("solana", "0" + "1" * 43),  # base58 has no 0
        ("solana", "O" * 44),  # base58 has no O/I/l
        ("solana", "5tz" + "a" * 20),  # too short
        ("avalanche", "0x" + "g" * 40),
        ("avalanche", "0x" + "a" * 39),
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
    [("evm", EVM), ("btc", BTC), ("ton", TON), ("tron", TRON), ("solana", SOLANA), ("avalanche", EVM)],
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
                        CryptoBalanceSnapshotModel.account_id == wallet_id,
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
                    account_id=wallet.id,
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
                        CryptoHoldingModel.account_id == wallet.id,
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
                    .where(CryptoBalanceSnapshotModel.account_id == wallet.id)
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
            (await session.execute(select(CryptoSyncRunModel).where(CryptoSyncRunModel.account_id == wallet.id)))
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
            (await session.execute(select(CryptoSyncRunModel).where(CryptoSyncRunModel.account_id == wallet.id)))
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
                        CryptoBalanceSnapshotModel.account_id == wallet.id,
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


# --- wallet IS the account -----------------------------------------------------


@pytest.mark.asyncio
async def test_wallet_create_owns_its_account(user, currencies, session_maker):
    async with session_maker() as session:
        session.add(CryptoPriceDailyModel(asset_code="BTC", day=date.today(), price_usd=Decimal("60000")))
        await session.commit()
    wallet = await CryptoService.create_for_user(
        WalletCreate(name="W", kind=WalletKind.MANUAL, holdings=[HoldingIn(asset_code="BTC", amount=1)]),
        user.id,
        session_maker,
    )
    # The wallet id is the account id: one object, visible to finance as an investment account.
    own = await AccountService.get_by_user(wallet.id, user.id, session_maker)
    assert own.name == "W"
    assert own.type == AccountType.INVESTMENT
    assert own.currency_id == "USD"
    assert own.crypto_kind == "manual"
    assert own.is_excluded is False
    assert own.balance == pytest.approx(60000.0)

    # Hand-editing holdings rewrites the account balance directly.
    await CryptoService.set_manual_holdings(
        wallet.id, [HoldingIn(asset_code="BTC", amount=0.5)], user.id, session_maker
    )
    own = await AccountService.get_by_user(wallet.id, user.id, session_maker)
    assert own.balance == pytest.approx(30000.0)

    # Deleting the wallet deletes the account (single lifecycle).
    await CryptoService.delete_for_user(wallet.id, user.id, session_maker)
    with pytest.raises(HTTPException) as error:
        await AccountService.get_by_user(wallet.id, user.id, session_maker)
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_rename_through_wallet_or_account(user, currencies, session_maker):
    wallet = await CryptoService.create_for_user(WalletCreate(name="W", kind=WalletKind.TRUST), user.id, session_maker)
    renamed = await CryptoService.update_for_user(wallet.id, WalletUpdate(name="X"), user.id, session_maker)
    assert renamed.name == "X"
    own = await AccountService.get_by_user(wallet.id, user.id, session_maker)
    assert own.name == "X"
    # Finance side may rename too: it is the same row.
    again = await AccountService.update_for_user(wallet.id, AccountUpdate(name="Y"), user.id, session_maker)
    assert again.name == "Y"


@pytest.mark.asyncio
async def test_finance_side_cannot_edit_wallet_fields(user, currencies, session_maker):
    wallet = await CryptoService.create_for_user(WalletCreate(name="W", kind=WalletKind.MANUAL), user.id, session_maker)
    for schema in (AccountUpdate(balance=5.0), AccountUpdate(currency_id="EUR"), AccountUpdate(type=AccountType.CASH)):
        with pytest.raises(HTTPException) as error:
            await AccountService.update_for_user(wallet.id, schema, user.id, session_maker)
        assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_transactions_on_wallet_account_rejected(user, account, session_maker):
    wallet = await CryptoService.create_for_user(WalletCreate(name="W", kind=WalletKind.MANUAL), user.id, session_maker)
    for source_id, target_id in ((wallet.id, account.id), (account.id, wallet.id)):
        with pytest.raises(HTTPException) as error:
            await TransactionService.create_for_user(
                TransactionCreate(
                    account_id=source_id,
                    amount=1.0,
                    currency_id="USD",
                    type=TransactionType.TRANSFER,
                    transfer_account_id=target_id,
                    date=datetime.now(),
                ),
                user.id,
                session_maker,
            )
        assert error.value.status_code == 400


# --- sync status on the wallet DTO ---------------------------------------------


@pytest.mark.asyncio
async def test_wallet_dto_carries_last_sync(user, currencies, session_maker):
    async with session_maker() as session:
        session.add(CryptoPriceDailyModel(asset_code="BTC", day=date.today(), price_usd=Decimal("60000")))
        await session.commit()
    wallet = await CryptoService.create_for_user(
        WalletCreate(name="W", kind=WalletKind.MANUAL, holdings=[HoldingIn(asset_code="BTC", amount=1)]),
        user.id,
        session_maker,
    )
    listing = await CryptoService.list_for_user(user.id, session_maker)
    item = listing.items[0]
    assert item.id == wallet.id
    assert item.last_sync_status == "ok"
    assert item.last_sync_at is not None


@pytest.mark.asyncio
async def test_last_sync_uses_latest_run(user, currencies, session_maker):
    wallet = await CryptoService.create_for_user(WalletCreate(name="W", kind=WalletKind.TRUST), user.id, session_maker)
    now = datetime.now()
    async with session_maker() as session:
        session.add_all(
            [
                CryptoSyncRunModel(account_id=wallet.id, status=SyncStatus.OK, started_at=now - timedelta(hours=2)),
                CryptoSyncRunModel(account_id=wallet.id, status=SyncStatus.ERROR, started_at=now - timedelta(hours=1)),
            ]
        )
        await session.commit()
    listing = await CryptoService.list_for_user(user.id, session_maker)
    assert listing.items[0].last_sync_status == "error"


# --- backfill self-heal ---------------------------------------------------------


@pytest.mark.asyncio
async def test_scheduler_rekicks_missing_backfill_once(user, currencies, session_maker, monkeypatch):
    crypto_service._SELFHEAL_KICKED.clear()
    wallet = await CryptoService.create_for_user(WalletCreate(name="W", kind=WalletKind.TRUST), user.id, session_maker)
    kicked: list = []
    monkeypatch.setattr(crypto_service, "kick_backfill", kicked.append)
    await run_syncs_once(session_maker)
    assert kicked == [wallet.id]
    await run_syncs_once(session_maker)  # second tick: already healed once this process
    assert kicked == [wallet.id]


@pytest.mark.asyncio
async def test_scheduler_does_not_rekick_wallet_with_history(user, currencies, session_maker, monkeypatch):
    crypto_service._SELFHEAL_KICKED.clear()
    wallet = await CryptoService.create_for_user(WalletCreate(name="W", kind=WalletKind.TRUST), user.id, session_maker)
    kicked: list = []
    monkeypatch.setattr(crypto_service, "kick_backfill", kicked.append)
    async with session_maker() as session:
        session.add(
            CryptoBalanceSnapshotModel(
                account_id=wallet.id,
                asset_code="BTC",
                day=date.today() - timedelta(days=5),
                amount=Decimal("1"),
                price_usd=None,
                source=SnapshotSource.BACKFILL,
                taken_at=datetime.now(),
            )
        )
        await session.commit()
    await run_syncs_once(session_maker)
    assert kicked == []


# --- solana / avalanche adapters -------------------------------------------------


def test_validate_address_new_chains():
    validate_address(Chain.SOLANA, SOLANA)  # no exception
    validate_address(Chain.AVALANCHE, EVM)  # no exception


def test_parse_solana_account():
    token_accounts = [
        {"account": {"data": {"parsed": {"info": {"tokenAmount": {"uiAmount": 207.3133}}}}}},
        {"account": {"data": {"parsed": {"info": {"tokenAmount": {"uiAmount": None}}}}}},
    ]
    holdings = dict(parse_solana_account(65746168004, token_accounts))
    assert holdings["SOL"] == Decimal("65.746168004")
    assert holdings["USDC"] == Decimal("207.3133")


def test_parse_solana_account_empty():
    assert parse_solana_account(0, []) == []


def test_parse_avalanche_balances():
    results = ["0xde0b6b3a7640000", "0x5f5e100", None]  # 1 AVAX, 100 USDC (6 decimals), USDT missing
    holdings = dict(parse_avalanche_balances(results))
    assert holdings == {"AVAX": Decimal("1"), "USDC": Decimal("100")}


@pytest.mark.asyncio
async def test_fetch_solana_holdings_rpc_shape(monkeypatch):
    calls: list = []

    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    class FakeClient:
        async def post(self, url, json=None):
            calls.append((url, json["method"], json["params"]))
            if json["method"] == "getBalance":
                return FakeResponse({"result": {"context": {}, "value": 1500000000}})
            return FakeResponse(
                {
                    "result": {
                        "value": [{"account": {"data": {"parsed": {"info": {"tokenAmount": {"uiAmount": 12.5}}}}}}]
                    }
                }
            )

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

    monkeypatch.setattr("src.crypto.adapters._client", lambda: FakeClient())
    holdings = dict(await crypto_service.adapters._fetch_solana_holdings(SOLANA))
    assert holdings == {"SOL": Decimal("1.5"), "USDC": Decimal("12.5")}
    assert [call[1] for call in calls] == ["getBalance", "getTokenAccountsByOwner"]
    assert calls[1][2][1] == {"mint": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"}
