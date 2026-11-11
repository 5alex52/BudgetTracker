"""USD prices for crypto assets via CoinGecko, cached per day in Postgres.

Cache-first: a (asset, day) row in ``crypto_price_daily`` is used before any
network call; missing days are fetched in bulk — one market_chart call per
asset, one simple/price call for all current prices — so the free tier's
~10-30 req/min limit is respected.
"""

import asyncio
import logging
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from typing import Dict
from typing import Iterable
from typing import List
from typing import Sequence
from typing import Tuple

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CryptoPriceDailyModel

logger = logging.getLogger(__name__)

COINGECKO_API = "https://api.coingecko.com/api/v3"
ASSET_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "USDC": "usd-coin",
    "DAI": "dai",
    "BNB": "binancecoin",
    "TON": "the-open-network",
    "TRX": "tron",
    "SOL": "solana",
    "AVAX": "avalanche-2",
}
#: Pause between per-asset historical calls keeps the free tier happy
REQUEST_PAUSE_SECONDS = 1.5
MAX_HISTORY_DAYS = 365
HEADERS = {"User-Agent": "BudgetTracker/1.0", "Accept": "application/json"}

PriceMap = Dict[Tuple[str, date], Decimal]


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=15.0, headers=HEADERS)


async def cached_daily_prices(session: AsyncSession, assets: Sequence[str], days: Iterable[date]) -> PriceMap:
    """(asset, day) -> USD price for rows already in the cache."""
    assets = list(assets)
    days = sorted(set(days))
    if not assets or not days:
        return {}
    rows = (
        (
            await session.execute(
                select(CryptoPriceDailyModel).where(
                    CryptoPriceDailyModel.asset_code.in_(assets),
                    CryptoPriceDailyModel.day >= days[0],
                    CryptoPriceDailyModel.day <= days[-1],
                )
            )
        )
        .scalars()
        .all()
    )
    return {(row.asset_code, row.day): row.price_usd for row in rows}


async def fetch_current_prices(assets: Sequence[str]) -> Dict[str, Decimal]:
    """Current USD prices; all assets in one simple/price call. {} on failure."""
    ids = [ASSET_IDS[asset] for asset in assets if asset in ASSET_IDS]
    if not ids:
        return {}
    try:
        async with _client() as client:
            response = await client.get(
                f"{COINGECKO_API}/simple/price",
                params={"ids": ",".join(ids), "vs_currencies": "usd"},
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as caught:
        logger.warning("CoinGecko current prices unavailable: %s", caught)
        return {}
    reverse = {cg_id: asset for asset, cg_id in ASSET_IDS.items()}
    return {reverse[cg_id]: Decimal(str(prices["usd"])) for cg_id, prices in data.items() if "usd" in prices}


async def fetch_daily(asset: str, start_day: date, end_day: date) -> Dict[date, Decimal]:
    """Daily USD prices for one asset in one market_chart call; {} on failure."""
    cg_id = ASSET_IDS.get(asset)
    if cg_id is None:
        return {}
    if (end_day - start_day).days > MAX_HISTORY_DAYS - 1:
        start_day = end_day - timedelta(days=MAX_HISTORY_DAYS - 1)
    try:
        async with _client() as client:
            response = await client.get(
                f"{COINGECKO_API}/coins/{cg_id}/market_chart",
                params={
                    "vs_currency": "usd",
                    "days": max(1, (end_day - start_day).days + 1),
                    "interval": "daily",
                },
            )
            response.raise_for_status()
            points = response.json().get("prices") or []
    except httpx.HTTPError as caught:
        logger.warning("CoinGecko daily prices unavailable for %s: %s", asset, caught)
        return {}
    result: Dict[date, Decimal] = {}
    for timestamp, price in points:
        day = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).date()
        if start_day <= day <= end_day:
            result[day] = Decimal(str(price))
    return result


async def daily_prices(session: AsyncSession, assets: Sequence[str], days: Iterable[date]) -> PriceMap:
    """(asset, day) -> USD price, cache-first, one CoinGecko call per missing asset."""
    days = sorted(set(days))
    result = await cached_daily_prices(session, assets, days)
    pause = False
    for asset in assets:
        missing = [day for day in days if (asset, day) not in result]
        if not missing:
            continue
        if pause:
            await asyncio.sleep(REQUEST_PAUSE_SECONDS)
        pause = True
        fetched = await fetch_daily(asset, missing[0], missing[-1])
        for day, price in fetched.items():
            session.add(CryptoPriceDailyModel(asset_code=asset, day=day, price_usd=price))
        result.update({(asset, day): price for day, price in fetched.items()})
    if assets:
        await session.commit()
    return result


async def latest_prices(session: AsyncSession, assets: Sequence[str]) -> Dict[str, Decimal]:
    """Latest known USD price per asset: cached rows first, CoinGecko only for gaps."""
    latest: Dict[str, Decimal] = {}
    if not assets:
        return latest
    rows = (
        (
            await session.execute(
                select(CryptoPriceDailyModel)
                .where(CryptoPriceDailyModel.asset_code.in_(list(assets)))
                .order_by(CryptoPriceDailyModel.asset_code, CryptoPriceDailyModel.day.desc())
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        latest.setdefault(row.asset_code, row.price_usd)
    missing = [asset for asset in assets if asset not in latest]
    if missing:
        current = await fetch_current_prices(missing)
        if current:
            today = datetime.now(timezone.utc).date()
            for asset, price in current.items():
                session.add(CryptoPriceDailyModel(asset_code=asset, day=today, price_usd=price))
            await session.commit()
            latest.update(current)
    return latest


def carry_prices_for_days(prices: PriceMap, assets: Sequence[str], days: List[date]) -> Dict[date, Dict[str, Decimal]]:
    """{day: {asset: price}} with the last known price carried into empty days."""
    by_asset: Dict[str, List[Tuple[date, Decimal]]] = {asset: [] for asset in assets}
    for (asset, day), price in sorted(prices.items()):
        if asset in by_asset:
            by_asset[asset].append((day, price))
    result: Dict[date, Dict[str, Decimal]] = {}
    pointers = {asset: 0 for asset in by_asset}
    for day in days:
        row: Dict[str, Decimal] = {}
        for asset, series in by_asset.items():
            while pointers[asset] < len(series) and series[pointers[asset]][0] <= day:
                row[asset] = series[pointers[asset]][1]
                pointers[asset] += 1
        if row:
            result[day] = row
    return result
