"""Chain adapters: read public data for watched addresses.

Everything here is read-only — public addresses queried against public RPC/API
endpoints, no keys required. Etherscan/Moralis keys only unlock richer EVM
backfill and are optional. All failures surface as a domain ``SyncError`` so
the service can record a ``crypto_sync_runs`` row instead of crashing.
"""

import logging
import os
import re
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from decimal import Decimal
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple

import httpx
from fastapi import HTTPException
from fastapi import status

from .schemas import Chain

logger = logging.getLogger(__name__)

BACKFILL_DAYS = 365
#: Sane caps so a huge history cannot turn one sync into a request storm
MAX_HISTORY_TXS = 250
MAX_TX_PAGES = 3
TIMEOUT = 15.0
HEADERS = {"User-Agent": "BudgetTracker/1.0", "Accept": "application/json"}

#: Public RPCs tried in order — single endpoints (llamarpc) intermittently return 5xx
EVM_RPCS = {
    "ETH": ["https://eth.llamarpc.com", "https://ethereum-rpc.publicnode.com", "https://cloudflare-eth.com"],
    "BNB": ["https://bsc-dataseed.binance.org", "https://bsc-rpc.publicnode.com"],
}

#: Curated well-known tokens (asset, contract, decimals); None contract = native coin
EVM_TOKENS = {
    "ETH": [
        ("ETH", None, 18),
        ("USDT", "0xdAC17F958D2ee523a2206206994597C13D831ec7", 6),
        ("USDC", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 6),
        ("DAI", "0x6B175474E89094C44Da98b954EedeAC495271d0F", 18),
    ],
    "BNB": [
        ("BNB", None, 18),
        ("USDT", "0x55d398326f99059fF775485246999027B3197955", 18),
        ("USDC", "0x8AC76a51cc950d9822d68b83fe1aD97b32Cd580d", 18),
        ("DAI", "0x1AF3F329e8BE154074D8769D1FFa4eE058B1DBc3", 18),
    ],
}

#: Well-known TRC20 contracts for the TronGrid fallback (Tronscan gives symbols itself)
TRON_TRC20 = {
    "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t": ("USDT", 6),
}

TON_JETTON_SYMBOLS = {"USD₮": "USDT"}

_ADDRESS_PATTERNS = {
    Chain.EVM: re.compile(r"^0x[0-9a-fA-F]{40}$"),
    Chain.BTC: re.compile(r"^(bc1[a-z0-9]{20,71}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$"),
    Chain.TON: re.compile(r"^(UQ|EQ)[A-Za-z0-9_-]{46}$|^[0-9a-fA-F]{64}$"),
    Chain.TRON: re.compile(r"^T[1-9A-HJ-NP-Za-km-z]{33}$"),
}

Holdings = List[Tuple[str, Decimal]]
DailyHistory = Dict[date, Dict[str, Decimal]]


class SyncError(Exception):
    """Network/parse failure of a chain adapter; recorded as a failed sync run."""


def validate_address(chain: Chain, address: str) -> None:
    """Trust boundary: only well-formed public addresses are accepted."""
    if not _ADDRESS_PATTERNS[chain].match(address or ""):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {chain.value} address",
        )


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS)


# --- EVM -------------------------------------------------------------------


def _balance_of_calldata(address: str) -> str:
    return "0x70a08231" + "0" * 24 + address[2:].lower()


async def _rpc_batch(client: httpx.AsyncClient, url: str, calls: List[Tuple[str, list]]) -> list:
    """One JSON-RPC batch request; falls back to a single-response shape."""
    payload = [
        {"jsonrpc": "2.0", "id": i, "method": method, "params": params} for i, (method, params) in enumerate(calls)
    ]
    response = await client.post(url, json=payload)
    response.raise_for_status()
    results = response.json()
    if isinstance(results, dict):
        results = [results]
    by_id = {item.get("id"): item for item in results}
    return [(by_id.get(i) or {}).get("result") for i in range(len(calls))]


def _balance_quantity(result: Optional[str], decimals: int) -> Decimal:
    """Parse a hex quantity; empty/`0x` results mean the contract is not on this chain."""
    try:
        return Decimal(int(result, 16)) / Decimal(10**decimals)
    except (TypeError, ValueError):
        return Decimal(0)


async def _fetch_evm_holdings(address: str) -> Holdings:
    holdings: Holdings = []
    calldata = _balance_of_calldata(address)
    async with _client() as client:
        for native, tokens in EVM_TOKENS.items():
            calls = [("eth_getBalance", [address, "latest"])]
            calls += [
                ("eth_call", [{"to": contract, "data": calldata}, "latest"])
                for _, contract, _ in tokens
                if contract is not None
            ]
            results = None
            last_error: Exception = SyncError(f"No RPC for {native}")
            for url in EVM_RPCS[native]:
                try:
                    results = await _rpc_batch(client, url, calls)
                    break
                except (httpx.HTTPError, ValueError) as error:
                    last_error = error
            if results is None:
                raise last_error
            amount = _balance_quantity(results[0], 18)
            if amount > 0:
                holdings.append((native, amount))
            for (asset, _, decimals), result in zip(tokens[1:], results[1:]):
                amount = _balance_quantity(result, decimals)
                if amount > 0:
                    holdings.append((asset, amount))
    return holdings


async def _fetch_evm_history(address: str, days: int) -> DailyHistory:
    """Daily native balance reconstructed from Etherscan tx lists; needs a key."""
    api_key = os.environ.get("CRYPTO_ETHERSCAN_API_KEY", "")
    if not api_key:
        return {}  # shortcut: no Etherscan key → EVM backfill is the current balance only
    end_day = datetime.now(timezone.utc).date()
    start_day = end_day - timedelta(days=min(days, BACKFILL_DAYS) - 1)
    explorers = {
        "ETH": "https://api.etherscan.io/api",
        "BNB": "https://api.bscscan.com/api",
    }
    by_day: Dict[date, Dict[str, Decimal]] = {}
    async with _client() as client:
        for native, url in explorers.items():
            transactions: List[dict] = []
            for page in range(1, MAX_TX_PAGES + 1):
                response = await client.get(
                    url,
                    params={
                        "module": "account",
                        "action": "txlist",
                        "address": address,
                        "startblock": 0,
                        "endblock": 99999999,
                        "page": page,
                        "offset": 1000,
                        "sort": "asc",
                        "apikey": api_key,
                    },
                )
                response.raise_for_status()
                body = response.json()
                rows = body.get("result") or [] if isinstance(body.get("result"), list) else []
                transactions += rows
                if len(rows) < 1000:
                    break
            running = Decimal(0)
            for tx in transactions:
                if int(tx.get("isError") or 0):
                    continue
                value = Decimal(int(tx.get("value") or 0)) / Decimal(10**18)
                if (tx.get("to") or "").lower() == address.lower():
                    running += value
                if (tx.get("from") or "").lower() == address.lower():
                    running -= value
                day = datetime.fromtimestamp(int(tx["timeStamp"]), tz=timezone.utc).date()
                if day >= start_day:
                    by_day.setdefault(day, {})[native] = running
    return _carry_forward(by_day, start_day, end_day)


# --- BTC -------------------------------------------------------------------


async def _fetch_btc_holdings(address: str) -> Holdings:
    async with _client() as client:
        response = await client.get(f"https://mempool.space/api/address/{address}")
        response.raise_for_status()
        stats = response.json()["chain_stats"]
    sats = stats["funded_txo_sum"] - stats["spent_txo_sum"]
    return [("BTC", Decimal(sats) / Decimal(100_000_000))] if sats > 0 else []


def _btc_tx_delta(tx: dict, address: str) -> int:
    """Net satoshi change of one transaction for the watched address."""
    received = sum(
        vin["prevout"]["value"]
        for vin in tx.get("vin") or []
        if vin.get("prevout") and vin["prevout"].get("scriptpubkey_address") == address
    )
    sent = sum(vout["value"] for vout in tx.get("vout") or [] if vout.get("scriptpubkey_address") == address)
    return received - sent


async def _fetch_btc_history(address: str, days: int) -> DailyHistory:
    end_day = datetime.now(timezone.utc).date()
    start_day = end_day - timedelta(days=min(days, BACKFILL_DAYS) - 1)
    transactions: List[dict] = []
    after = ""
    async with _client() as client:
        while len(transactions) < MAX_HISTORY_TXS:
            url = f"https://mempool.space/api/address/{address}/txs/chain" + (f"/{after}" if after else "")
            response = await client.get(url)
            response.raise_for_status()
            page = response.json()
            if not page:
                break
            transactions += page
            after = page[-1]["txid"]
    by_day: Dict[date, Dict[str, Decimal]] = {}
    running = 0
    for tx in sorted(transactions, key=lambda item: item.get("block_time") or 0):
        running += _btc_tx_delta(tx, address)
        if tx.get("block_time"):
            day = datetime.fromtimestamp(tx["block_time"], tz=timezone.utc).date()
            if day >= start_day:
                by_day[day] = {"BTC": Decimal(running) / Decimal(100_000_000)}
    return _carry_forward(by_day, start_day, end_day)


# --- TON -------------------------------------------------------------------


async def _fetch_ton_holdings(address: str) -> Holdings:
    holdings: Holdings = []
    async with _client() as client:
        response = await client.get(f"https://tonapi.io/v2/accounts/{address}")
        response.raise_for_status()
        account = response.json()
        nanotons = int(account.get("balance") or 0)
        if nanotons > 0:
            holdings.append(("TON", Decimal(nanotons) / Decimal(10**9)))
        try:
            jettons = await client.get(f"https://tonapi.io/v2/accounts/{address}/jettons")
            jettons.raise_for_status()
            for item in jettons.json().get("balances") or []:
                jetton = item.get("jetton") or {}
                symbol = jetton.get("symbol") or ""
                asset = TON_JETTON_SYMBOLS.get(symbol, symbol.upper())
                decimals = int(jetton.get("decimals") or 9)
                amount = Decimal(int(item.get("balance") or 0)) / Decimal(10**decimals)
                if amount > 0 and asset:
                    holdings.append((asset[:16], amount))
        except (httpx.HTTPError, ValueError, KeyError):  # noqa: BLE001 — jettons are optional
            pass
    return holdings


async def _fetch_ton_history(address: str, days: int) -> DailyHistory:
    end_day = datetime.now(timezone.utc).date()
    start_day = end_day - timedelta(days=min(days, BACKFILL_DAYS) - 1)
    async with _client() as client:
        response = await client.get(
            f"https://tonapi.io/v2/accounts/{address}/history",
            params={"start_date": start_day.isoformat(), "end_date": end_day.isoformat()},
        )
        response.raise_for_status()
        rows = response.json()
    rows = rows.get("balances", rows) if isinstance(rows, dict) else rows
    by_day: DailyHistory = {}
    for row in rows or []:
        day = date.fromisoformat(str(row["date"])[:10])
        by_day[day] = {"TON": Decimal(str(row["balance"])) / Decimal(10**9)}
    return _carry_forward(by_day, start_day, end_day)


# --- TRON ------------------------------------------------------------------


def parse_tronscan_account(payload: dict) -> Holdings:
    """Pure parsing of a Tronscan accountv2 response (unit-tested, no HTTP)."""
    holdings: Holdings = []
    trx = Decimal(payload.get("balance") or 0) / Decimal(10**6)
    if trx > 0:
        holdings.append(("TRX", trx))
    for token in payload.get("tokenBalances") or []:
        if token.get("tokenType") != "trc20":
            continue
        asset = (token.get("tokenAbbr") or token.get("tokenName") or "").upper()[:16]
        decimals = int(token.get("tokenDecimal") or 0)
        amount = Decimal(token.get("balance") or 0) / Decimal(10**decimals)
        if amount > 0 and asset:
            holdings.append((asset, amount))
    return holdings


async def _fetch_tron_holdings(address: str) -> Holdings:
    try:
        async with _client() as client:
            response = await client.get("https://apilist.tronscanapi.com/api/accountv2", params={"address": address})
            response.raise_for_status()
            return parse_tronscan_account(response.json())
    except Exception:  # noqa: BLE001 — Tronscan is flaky; fall back to TronGrid
        logger.info("Tronscan failed for %s, falling back to TronGrid", address)
    async with _client() as client:
        response = await client.get(f"https://api.trongrid.io/v1/accounts/{address}")
        response.raise_for_status()
        account = (response.json().get("data") or [{}])[0]
    holdings: Holdings = []
    trx = Decimal(account.get("balance") or 0) / Decimal(10**6)
    if trx > 0:
        holdings.append(("TRX", trx))
    for entry in account.get("trc20") or []:
        for contract, raw in entry.items():
            meta = TRON_TRC20.get(contract)
            if meta and Decimal(raw) > 0:
                holdings.append((meta[0], Decimal(raw) / Decimal(10 ** meta[1])))
    return holdings


async def _fetch_tron_history(address: str, days: int) -> DailyHistory:
    """Daily balances from native/TRC20 transfers; approximate (starts from zero)."""
    end_day = datetime.now(timezone.utc).date()
    start_day = end_day - timedelta(days=min(days, BACKFILL_DAYS) - 1)
    start_ts = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp() * 1000)
    deltas: Dict[Tuple[date, str], Decimal] = {}
    async with _client() as client:
        for start in range(0, MAX_HISTORY_TXS, 200):
            response = await client.get(
                "https://apilist.tronscanapi.com/api/transfer",
                params={"address": address, "limit": 200, "start": start, "sort": "-timestamp"},
            )
            response.raise_for_status()
            rows = response.json().get("data") or []
            for row in rows:
                token = row.get("tokenInfo") or {}
                asset = (token.get("abbr") or "TRX").upper()[:16]
                decimals = int(token.get("decimals") or 0)
                amount = Decimal(str(row.get("amount") or 0)) / Decimal(10**decimals)
                if (row.get("to") or "") == address:
                    key = (datetime.fromtimestamp((row.get("timestamp") or 0) / 1000, tz=timezone.utc).date(), asset)
                    deltas[key] = deltas.get(key, Decimal(0)) + amount
                if (row.get("from") or "") == address:
                    key = (datetime.fromtimestamp((row.get("timestamp") or 0) / 1000, tz=timezone.utc).date(), asset)
                    deltas[key] = deltas.get(key, Decimal(0)) - amount
            if len(rows) < 200:
                break
    by_day: DailyHistory = {}
    running: Dict[str, Decimal] = {}
    for (day, asset), delta in sorted(deltas.items()):
        if day < start_day:
            continue
        running[asset] = running.get(asset, Decimal(0)) + delta
        by_day.setdefault(day, {})[asset] = running[asset]
    return _carry_forward(by_day, start_day, end_day)


# --- dispatch ---------------------------------------------------------------


_FETCHERS = {
    Chain.EVM: (_fetch_evm_holdings, _fetch_evm_history),
    Chain.BTC: (_fetch_btc_holdings, _fetch_btc_history),
    Chain.TON: (_fetch_ton_holdings, _fetch_ton_history),
    Chain.TRON: (_fetch_tron_holdings, _fetch_tron_history),
}


def _carry_forward(by_day: Dict[date, Dict[str, Decimal]], start_day: date, end_day: date) -> DailyHistory:
    """Daily series with the last known per-asset balance carried into empty days."""
    result: DailyHistory = {}
    balance: Dict[str, Decimal] = {}
    day = start_day
    while day <= end_day:
        balance.update(by_day.get(day, {}))
        if balance:
            result[day] = dict(balance)
        day += timedelta(days=1)
    return result


async def fetch_holdings(chain: Chain, address: str) -> Holdings:
    """(asset_code, amount) of everything the address currently holds."""
    try:
        return await _FETCHERS[chain][0](address)
    except SyncError:
        raise
    except Exception as caught:  # noqa: BLE001 — one domain error for any network/parse failure
        logger.warning("Holdings fetch failed for %s %s: %s", chain.value, address, caught)
        raise SyncError(str(caught))


async def fetch_daily_history(chain: Chain, address: str, days: int = BACKFILL_DAYS) -> DailyHistory:
    """{day: {asset: amount}} for up to ``days`` days; {} when unavailable."""
    if days > BACKFILL_DAYS:
        days = BACKFILL_DAYS
    try:
        return await _FETCHERS[chain][1](address, days)
    except SyncError:
        raise
    except Exception as caught:  # noqa: BLE001 — history is best-effort: {} → current snapshot only
        logger.warning("History fetch failed for %s %s: %s", chain.value, address, caught)
        return {}
