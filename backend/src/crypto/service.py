"""Crypto wallet tracking: read-only public addresses, daily snapshots, USD prices.

Vertical slice: DAO -> service -> router. Balances come from chain adapters
(``adapters.py``), prices from CoinGecko (``prices.py``); every USD value is
converted into the user's base currency with the same rates the rest of the
app uses. Nothing here can ever move funds: only public addresses are stored.
"""

import asyncio
import logging
from datetime import date
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..database import async_session_maker
from ..finance.service_subs import _rates
from ..finance.utils import convert_amount
from . import adapters
from . import prices
from .models import CryptoAddressModel
from .models import CryptoBalanceSnapshotModel
from .models import CryptoHoldingModel
from .models import CryptoSyncRunModel
from .models import CryptoWalletModel
from .schemas import AddressDTO
from .schemas import AssetBreakdown
from .schemas import BalancesDTO
from .schemas import Chain
from .schemas import HoldingDTO
from .schemas import HoldingIn
from .schemas import OverviewDTO
from .schemas import SnapshotSource
from .schemas import SyncStatus
from .schemas import WalletBreakdown
from .schemas import WalletCreate
from .schemas import WalletDTO
from .schemas import WalletKind
from .schemas import WalletList
from .schemas import WalletUpdate

logger = logging.getLogger(__name__)

MAX_ADDRESSES_PER_WALLET = 20
#: How often the background worker refreshes every wallet
SYNC_INTERVAL_SECONDS = 300

#: period -> days back from today (None = from the first snapshot)
PERIOD_DAYS: Dict[str, Optional[int]] = {"7d": 7, "30d": 30, "90d": 90, "1y": 365, "all": None}


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")


def _usd_to_base(value_usd: float, rates: dict, base_rate: float) -> float:
    """USD is the catalog base, so this is the same conversion finance applies to USD amounts."""
    return convert_amount(value_usd, rates.get("USD", 1.0), base_rate)


def _days_between(start_day: date, end_day: date) -> List[date]:
    return [start_day + timedelta(days=index) for index in range((end_day - start_day).days + 1)]


def _period_range(period: str, earliest_day: Optional[date]) -> Tuple[date, date]:
    end_day = datetime.now().date()
    days = PERIOD_DAYS[period]
    if days is None:
        return (earliest_day or end_day, end_day)
    return (end_day - timedelta(days=days - 1), end_day)


def _change_percent(now_value: float, start_value: float) -> Optional[float]:
    return round((now_value - start_value) / start_value * 100, 2) if start_value > 0 else None


async def _upsert_holding(session: AsyncSession, wallet_id: int, asset_code: str, amount: Decimal) -> None:
    row = (
        (
            await session.execute(
                select(CryptoHoldingModel).where(
                    CryptoHoldingModel.wallet_id == wallet_id,
                    CryptoHoldingModel.asset_code == asset_code,
                )
            )
        )
        .scalars()
        .one_or_none()
    )
    if row is None:
        session.add(CryptoHoldingModel(wallet_id=wallet_id, asset_code=asset_code, amount=amount))
    else:
        row.amount = amount
        row.updated_at = datetime.now()


async def _upsert_snapshot(
    session: AsyncSession,
    wallet_id: int,
    asset_code: str,
    day: date,
    amount: Decimal,
    price_usd: Optional[Decimal],
    source: SnapshotSource,
) -> None:
    """One snapshot per (wallet, asset, day); the latest write wins."""
    row = (
        (
            await session.execute(
                select(CryptoBalanceSnapshotModel).where(
                    CryptoBalanceSnapshotModel.wallet_id == wallet_id,
                    CryptoBalanceSnapshotModel.asset_code == asset_code,
                    CryptoBalanceSnapshotModel.day == day,
                )
            )
        )
        .scalars()
        .one_or_none()
    )
    if row is None:
        session.add(
            CryptoBalanceSnapshotModel(
                wallet_id=wallet_id,
                asset_code=asset_code,
                day=day,
                amount=amount,
                price_usd=price_usd,
                source=source,
                taken_at=datetime.now(),
            )
        )
    else:
        row.amount = amount
        row.price_usd = price_usd
        row.source = source
        row.taken_at = datetime.now()


async def _wallet_rows(user_id, session: AsyncSession) -> List[CryptoBalanceSnapshotModel]:
    wallet_ids = (
        (await session.execute(select(CryptoWalletModel.id).where(CryptoWalletModel.user_id == user_id)))
        .scalars()
        .all()
    )
    if not wallet_ids:
        return []
    return list(
        (
            await session.execute(
                select(CryptoBalanceSnapshotModel)
                .where(CryptoBalanceSnapshotModel.wallet_id.in_(wallet_ids))
                .order_by(CryptoBalanceSnapshotModel.day)
            )
        )
        .scalars()
        .all()
    )


def _daily_amounts(
    rows: List[CryptoBalanceSnapshotModel], start_day: date, end_day: date
) -> Dict[date, Dict[Tuple[int, str], Decimal]]:
    """{day: {(wallet, asset): amount}} with the latest snapshot ≤ day carried forward."""
    by_key: Dict[Tuple[int, str], List[CryptoBalanceSnapshotModel]] = {}
    for row in rows:
        by_key.setdefault((row.wallet_id, row.asset_code), []).append(row)
    pointers = {key: 0 for key in by_key}
    result: Dict[date, Dict[Tuple[int, str], Decimal]] = {}
    for day in _days_between(start_day, end_day):
        current: Dict[Tuple[int, str], Decimal] = {}
        for key, day_rows in by_key.items():
            index = pointers[key]
            while index < len(day_rows) and day_rows[index].day <= day:
                current[key] = day_rows[index].amount
                index += 1
            pointers[key] = index
        if current:
            result[day] = current
    return result


class CryptoDAO:
    @classmethod
    async def find_wallet_by_user(cls, session: AsyncSession, wallet_id: int, user_id) -> Optional[CryptoWalletModel]:
        stmt = (
            select(CryptoWalletModel)
            .where(CryptoWalletModel.id == wallet_id, CryptoWalletModel.user_id == user_id)
            .options(selectinload(CryptoWalletModel.addresses), selectinload(CryptoWalletModel.holdings))
        )
        return (await session.execute(stmt)).scalars().one_or_none()

    @classmethod
    async def find_all_by_user(cls, session: AsyncSession, user_id) -> List[CryptoWalletModel]:
        stmt = (
            select(CryptoWalletModel)
            .where(CryptoWalletModel.user_id == user_id)
            .options(selectinload(CryptoWalletModel.addresses), selectinload(CryptoWalletModel.holdings))
            .order_by(CryptoWalletModel.id)
        )
        return list((await session.execute(stmt)).scalars().all())


def kick_backfill(wallet_id: int) -> None:
    """Fire-and-forget backfill with its own session maker: survives client disconnects."""
    if settings.ENVIRONMENT == "TEST":
        return  # tests drive backfill explicitly with mocked adapters

    async def _job() -> None:
        try:
            await run_wallet_sync(wallet_id, async_session_maker, SnapshotSource.BACKFILL, include_history=True)
        except Exception:
            logger.exception("Crypto backfill failed for wallet %s", wallet_id)

    asyncio.create_task(_job())


async def run_wallet_sync(
    wallet_id: int,
    session_maker: async_sessionmaker,
    source: SnapshotSource,
    include_history: bool = False,
) -> str:
    """Refresh one wallet and persist holdings + snapshots + a sync_runs row.

    Manual wallets (telegram/manual kinds) never touch the network: their daily
    snapshot is written from hand-entered holdings. Returns the sync status.
    """
    started_at = datetime.now()
    today = datetime.now().date()
    async with session_maker() as session:
        wallet = (
            (
                await session.execute(
                    select(CryptoWalletModel)
                    .where(CryptoWalletModel.id == wallet_id)
                    .options(selectinload(CryptoWalletModel.addresses))
                )
            )
            .scalars()
            .one_or_none()
        )
        addresses = (
            [item for item in wallet.addresses if item.is_active]
            if wallet is not None and wallet.kind == WalletKind.TRUST
            else []
        )
    if not addresses:
        # Manual wallet or wallet without addresses: snapshot from current holdings
        async with session_maker() as session:
            holding_rows = (
                (await session.execute(select(CryptoHoldingModel).where(CryptoHoldingModel.wallet_id == wallet_id)))
                .scalars()
                .all()
            )
            if holding_rows:
                prices_map = await prices.daily_prices(session, [row.asset_code for row in holding_rows], [today])
                for holding in holding_rows:
                    await _upsert_snapshot(
                        session,
                        wallet_id,
                        holding.asset_code,
                        today,
                        holding.amount,
                        prices_map.get((holding.asset_code, today)),
                        SnapshotSource.MANUAL,
                    )
            session.add(
                CryptoSyncRunModel(
                    wallet_id=wallet_id, status=SyncStatus.OK, started_at=started_at, finished_at=datetime.now()
                )
            )
            await session.commit()
        return SyncStatus.OK.value

    sync_status = SyncStatus.OK
    error_text: Optional[str] = None
    holdings: Dict[str, Decimal] = {}
    history: Dict[date, Dict[str, Decimal]] = {}
    for address in addresses:
        try:
            for asset, amount in await adapters.fetch_holdings(address.chain, address.address):
                holdings[asset] = holdings.get(asset, Decimal(0)) + amount
        except adapters.SyncError as caught:
            sync_status = SyncStatus.PARTIAL if holdings else SyncStatus.ERROR
            error_text = str(caught)
        if include_history:
            try:
                daily = await adapters.fetch_daily_history(address.chain, address.address)
                for day, amounts in daily.items():
                    bucket = history.setdefault(day, {})
                    for asset, amount in amounts.items():
                        bucket[asset] = bucket.get(asset, Decimal(0)) + amount
            except adapters.SyncError as caught:
                sync_status = SyncStatus.PARTIAL if (holdings or history) else SyncStatus.ERROR
                error_text = error_text or str(caught)

    async with session_maker() as session:
        for asset, amount in holdings.items():
            await _upsert_holding(session, wallet_id, asset, amount)
        await session.commit()
        wanted_assets = sorted(set(holdings) | {asset for amounts in history.values() for asset in amounts})
        if wanted_assets:
            wanted_days = sorted(set(history) | {today})
            prices_map = await prices.daily_prices(session, wanted_assets, wanted_days)
            for day, amounts in history.items():
                for asset, amount in amounts.items():
                    await _upsert_snapshot(
                        session, wallet_id, asset, day, amount, prices_map.get((asset, day)), SnapshotSource.BACKFILL
                    )
            for asset, amount in holdings.items():
                await _upsert_snapshot(session, wallet_id, asset, today, amount, prices_map.get((asset, today)), source)
        session.add(
            CryptoSyncRunModel(
                wallet_id=wallet_id,
                status=sync_status,
                error=error_text,
                started_at=started_at,
                finished_at=datetime.now(),
            )
        )
        await session.commit()
    return sync_status.value


async def run_syncs_once(session_maker: async_sessionmaker) -> int:
    """One scheduler tick: refresh every wallet; returns wallets processed."""
    async with session_maker() as session:
        wallet_rows = (await session.execute(select(CryptoWalletModel.id, CryptoWalletModel.kind))).all()
    processed = 0
    for wallet_id, _kind in wallet_rows:
        try:
            await run_wallet_sync(wallet_id, session_maker, SnapshotSource.SCHEDULER)
            processed += 1
        except Exception:
            logger.exception("Crypto sync failed for wallet %s", wallet_id)
    return processed


async def crypto_sync_loop(session_maker: async_sessionmaker, interval: int = SYNC_INTERVAL_SECONDS) -> None:
    """Background worker: refresh every wallet's holdings every ``interval`` seconds."""
    while True:
        try:
            await run_syncs_once(session_maker)
        except Exception:
            logger.exception("Crypto sync run failed")
        await asyncio.sleep(interval)


class CryptoService:
    dao = CryptoDAO

    @classmethod
    async def _wallet_or_404(cls, session: AsyncSession, wallet_id: int, user_id) -> CryptoWalletModel:
        wallet = await cls.dao.find_wallet_by_user(session, wallet_id, user_id)
        if wallet is None:
            raise _not_found()
        return wallet

    @classmethod
    async def _holding_dtos(
        cls, session: AsyncSession, holding_rows: List[CryptoHoldingModel], user_id
    ) -> Tuple[str, float, float, List[HoldingDTO]]:
        """(base currency, total USD, total base, holding DTOs) for a list of holdings."""
        base_code, base_rate, rates = await _rates(session, user_id)
        current = await prices.latest_prices(session, sorted({row.asset_code for row in holding_rows}))
        items: List[HoldingDTO] = []
        total_usd = 0.0
        total_base = 0.0
        for holding in holding_rows:
            price = current.get(holding.asset_code)
            value_usd = round(float(holding.amount) * float(price), 2) if price is not None else None
            value_base = _usd_to_base(value_usd, rates, base_rate) if value_usd is not None else None
            if value_usd is not None:
                total_usd += value_usd
                total_base += value_base
            items.append(
                HoldingDTO(
                    asset_code=holding.asset_code,
                    amount=float(holding.amount),
                    price_usd=float(price) if price is not None else None,
                    value_usd=value_usd,
                    value_base=value_base,
                )
            )
        return base_code, round(total_usd, 2), round(total_base, 2), items

    @classmethod
    async def _wallet_dto(cls, session: AsyncSession, wallet: CryptoWalletModel, user_id) -> WalletDTO:
        base_code, total_usd, total_base, holdings = await cls._holding_dtos(session, wallet.holdings, user_id)
        return WalletDTO(
            id=wallet.id,
            name=wallet.name,
            kind=wallet.kind,
            addresses=[
                AddressDTO(id=item.id, chain=item.chain, address=item.address, is_active=item.is_active)
                for item in wallet.addresses
            ],
            holdings=holdings,
            total_usd=total_usd,
            total_base=total_base,
            base_currency=base_code,
            created_at=wallet.created_at,
            updated_at=wallet.updated_at,
        )

    @classmethod
    async def list_for_user(cls, user_id, session_maker: async_sessionmaker) -> WalletList:
        async with session_maker() as session:
            wallets = await cls.dao.find_all_by_user(session, user_id)
            items = [await cls._wallet_dto(session, wallet, user_id) for wallet in wallets]
        return WalletList(
            items=items,
            total_usd=round(sum(item.total_usd for item in items), 2),
            total_base=round(sum(item.total_base for item in items), 2),
            base_currency=items[0].base_currency if items else "USD",
        )

    @classmethod
    async def create_for_user(cls, schema: WalletCreate, user_id, session_maker: async_sessionmaker) -> WalletDTO:
        seen = set()
        for item in schema.addresses or []:
            adapters.validate_address(item.chain, item.address)
            key = (item.chain, item.address)
            if key in seen:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate address")
            seen.add(key)
        manual = schema.kind != WalletKind.TRUST
        async with session_maker() as session:
            wallet = CryptoWalletModel(user_id=user_id, name=schema.name, kind=schema.kind)
            session.add(wallet)
            await session.flush()
            for item in schema.addresses or []:
                session.add(CryptoAddressModel(wallet_id=wallet.id, chain=item.chain, address=item.address))
            for item in schema.holdings or []:
                if not manual:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="holdings are only allowed for manual wallets",
                    )
                await _upsert_holding(session, wallet.id, item.asset_code.upper(), Decimal(str(item.amount)))
            await session.commit()
            wallet_id = wallet.id
        if not manual:
            kick_backfill(wallet_id)
        elif schema.holdings:
            # Snapshot today's starting balance so the timeseries starts now, not at zero
            await run_wallet_sync(wallet_id, session_maker, SnapshotSource.MANUAL)
        async with session_maker() as session:
            wallet = await cls._wallet_or_404(session, wallet_id, user_id)
            return await cls._wallet_dto(session, wallet, user_id)

    @classmethod
    async def update_for_user(
        cls, wallet_id: int, schema: WalletUpdate, user_id, session_maker: async_sessionmaker
    ) -> WalletDTO:
        async with session_maker() as session:
            wallet = await cls._wallet_or_404(session, wallet_id, user_id)
            data = schema.model_dump(exclude_unset=True)
            for field, value in data.items():
                setattr(wallet, field, value)
            await session.commit()
        async with session_maker() as session:
            wallet = await cls._wallet_or_404(session, wallet_id, user_id)
            return await cls._wallet_dto(session, wallet, user_id)

    @classmethod
    async def delete_for_user(cls, wallet_id: int, user_id, session_maker: async_sessionmaker) -> None:
        async with session_maker() as session:
            wallet = await cls._wallet_or_404(session, wallet_id, user_id)
            await session.delete(wallet)
            await session.commit()

    @classmethod
    async def add_address(
        cls, wallet_id: int, chain: Chain, address: str, user_id, session_maker: async_sessionmaker
    ) -> WalletDTO:
        adapters.validate_address(chain, address)
        async with session_maker() as session:
            wallet = await cls._wallet_or_404(session, wallet_id, user_id)
            if len(wallet.addresses) >= MAX_ADDRESSES_PER_WALLET:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Wallet cannot have more than {MAX_ADDRESSES_PER_WALLET} addresses",
                )
            if any(item.chain == chain and item.address == address for item in wallet.addresses):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Address already added")
            session.add(CryptoAddressModel(wallet_id=wallet_id, chain=chain, address=address))
            await session.commit()
        if wallet.kind == WalletKind.TRUST:
            kick_backfill(wallet_id)
        async with session_maker() as session:
            wallet = await cls._wallet_or_404(session, wallet_id, user_id)
            return await cls._wallet_dto(session, wallet, user_id)

    @classmethod
    async def delete_address(cls, wallet_id: int, address_id: int, user_id, session_maker: async_sessionmaker) -> None:
        async with session_maker() as session:
            wallet = await cls._wallet_or_404(session, wallet_id, user_id)
            address = (
                (
                    await session.execute(
                        select(CryptoAddressModel).where(
                            CryptoAddressModel.id == address_id,
                            CryptoAddressModel.wallet_id == wallet.id,
                        )
                    )
                )
                .scalars()
                .one_or_none()
            )
            if address is None:
                raise _not_found()
            await session.delete(address)
            await session.commit()

    @classmethod
    async def balances_dto(
        cls, wallet: CryptoWalletModel, user_id, session: AsyncSession, sync_status: Optional[str] = None
    ) -> BalancesDTO:
        base_code, total_usd, total_base, holdings = await cls._holding_dtos(session, wallet.holdings, user_id)
        return BalancesDTO(
            wallet_id=wallet.id,
            status=sync_status,
            holdings=holdings,
            total_usd=total_usd,
            total_base=total_base,
            base_currency=base_code,
        )

    @classmethod
    async def balances(cls, wallet_id: int, user_id, session_maker: async_sessionmaker) -> BalancesDTO:
        async with session_maker() as session:
            wallet = await cls._wallet_or_404(session, wallet_id, user_id)
            return await cls.balances_dto(wallet, user_id, session)

    @classmethod
    async def sync_now(cls, wallet_id: int, user_id, session_maker: async_sessionmaker) -> BalancesDTO:
        async with session_maker() as session:
            wallet = await cls._wallet_or_404(session, wallet_id, user_id)
        sync_status = await run_wallet_sync(wallet_id, session_maker, SnapshotSource.SCHEDULER)
        async with session_maker() as session:
            wallet = await cls._wallet_or_404(session, wallet_id, user_id)
            return await cls.balances_dto(wallet, user_id, session, sync_status=sync_status)

    @classmethod
    async def set_manual_holdings(
        cls, wallet_id: int, holdings: List[HoldingIn], user_id, session_maker: async_sessionmaker
    ) -> BalancesDTO:
        async with session_maker() as session:
            wallet = await cls._wallet_or_404(session, wallet_id, user_id)
            if wallet.kind == WalletKind.TRUST:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only manual wallets accept hand-entered balances",
                )
            for holding in list(wallet.holdings):
                await session.delete(holding)
            for item in holdings:
                await _upsert_holding(session, wallet_id, item.asset_code.upper(), Decimal(str(item.amount)))
            await session.commit()
            today = datetime.now().date()
            codes = [item.asset_code.upper() for item in holdings]
            prices_map = await prices.daily_prices(session, codes, [today])
            for item in holdings:
                code = item.asset_code.upper()
                await _upsert_snapshot(
                    session,
                    wallet_id,
                    code,
                    today,
                    Decimal(str(item.amount)),
                    prices_map.get((code, today)),
                    SnapshotSource.MANUAL,
                )
            await session.commit()
        async with session_maker() as session:
            wallet = await cls._wallet_or_404(session, wallet_id, user_id)
            return await cls.balances_dto(wallet, user_id, session)

    @classmethod
    async def overview(cls, user_id, period: str, session_maker: async_sessionmaker) -> OverviewDTO:
        async with session_maker() as session:
            wallets = await cls.dao.find_all_by_user(session, user_id)
            base_code, base_rate, rates = await _rates(session, user_id)
            rows = await _wallet_rows(user_id, session)
            holdings = [holding for wallet in wallets for holding in wallet.holdings]
            assets = sorted({row.asset_code for row in rows} | {holding.asset_code for holding in holdings})
            start_day, end_day = _period_range(period, rows[0].day if rows else None)
            prices_map = await prices.cached_daily_prices(session, assets, _days_between(start_day, end_day))
            now_prices = await prices.latest_prices(session, assets)
        # Value at period start: latest snapshot ≤ start_day × price at start_day
        start_amounts: Dict[Tuple[int, str], Decimal] = {}
        for row in rows:
            if row.day <= start_day:
                start_amounts[(row.wallet_id, row.asset_code)] = row.amount
        start_prices = prices.carry_prices_for_days(prices_map, assets, [start_day]).get(start_day, {})
        start_by_asset: Dict[str, float] = {}
        start_by_wallet: Dict[int, float] = {}
        start_total = 0.0
        for (wallet_id, asset), amount in start_amounts.items():
            price = start_prices.get(asset)
            if price is None:
                continue
            value = _usd_to_base(float(amount) * float(price), rates, base_rate)
            start_by_asset[asset] = round(start_by_asset.get(asset, 0.0) + value, 2)
            start_by_wallet[wallet_id] = round(start_by_wallet.get(wallet_id, 0.0) + value, 2)
            start_total += value
        # Now: current holdings × latest known price
        now_by_asset: Dict[str, Dict[str, float]] = {}
        now_by_wallet: Dict[int, float] = {}
        now_total = 0.0
        for holding in holdings:
            price = now_prices.get(holding.asset_code)
            if price is None:
                continue
            value = _usd_to_base(float(holding.amount) * float(price), rates, base_rate)
            asset = now_by_asset.setdefault(
                holding.asset_code, {"amount": 0.0, "price_usd": float(price), "value_base": 0.0}
            )
            asset["amount"] += float(holding.amount)
            asset["value_base"] += value
            now_by_wallet[holding.wallet_id] = now_by_wallet.get(holding.wallet_id, 0.0) + value
            now_total += value
        by_asset = [
            AssetBreakdown(
                asset_code=asset,
                amount=round(data["amount"], 12),
                price_usd=data["price_usd"],
                value_base=round(data["value_base"], 2),
                change_percent=_change_percent(data["value_base"], start_by_asset.get(asset, 0.0)),
            )
            for asset, data in sorted(now_by_asset.items())
        ]
        by_wallet = [
            WalletBreakdown(
                wallet_id=wallet.id,
                name=wallet.name,
                value_base=round(now_by_wallet.get(wallet.id, 0.0), 2),
                change_percent=_change_percent(now_by_wallet.get(wallet.id, 0.0), start_by_wallet.get(wallet.id, 0.0)),
            )
            for wallet in wallets
        ]
        return OverviewDTO(
            period=period,
            base_currency=base_code,
            total_now_base=round(now_total, 2),
            change_absolute=round(now_total - start_total, 2),
            change_percent=_change_percent(now_total, start_total),
            by_asset=by_asset,
            by_wallet=by_wallet,
        )

    @classmethod
    async def timeseries(cls, user_id, period: str, group_by: str, session_maker: async_sessionmaker) -> dict:
        async with session_maker() as session:
            base_code, base_rate, rates = await _rates(session, user_id)
            rows = await _wallet_rows(user_id, session)
            start_day, end_day = _period_range(period, rows[0].day if rows else None)
            assets = sorted({row.asset_code for row in rows})
            days = _days_between(start_day, end_day)
            prices_map = await prices.cached_daily_prices(session, assets, days)
        carried_prices = prices.carry_prices_for_days(prices_map, assets, days)
        daily_amounts = _daily_amounts(rows, start_day, end_day)
        points = []
        for day in days:
            by_asset: Dict[str, float] = {}
            by_wallet: Dict[str, float] = {}
            total = 0.0
            for (wallet_id, asset), amount in daily_amounts.get(day, {}).items():
                price = carried_prices.get(day, {}).get(asset)
                if price is None:
                    continue
                value = _usd_to_base(float(amount) * float(price), rates, base_rate)
                by_asset[asset] = round(by_asset.get(asset, 0.0) + value, 2)
                by_wallet[str(wallet_id)] = round(by_wallet.get(str(wallet_id), 0.0) + value, 2)
                total += value
            points.append(
                {
                    "day": day,
                    "total_base": round(total, 2),
                    "by_asset": by_asset,
                    "by_wallet": by_wallet,
                }
            )
        return {"period": period, "group_by": group_by, "base_currency": base_code, "points": points}

    @classmethod
    async def asset_codes(cls, user_id, session_maker: async_sessionmaker) -> List[str]:
        async with session_maker() as session:
            wallets = await cls.dao.find_all_by_user(session, user_id)
            return sorted({holding.asset_code for wallet in wallets for holding in wallet.holdings})
