"""HTTP endpoints for the crypto wallet tracker (prefix /api/crypto)."""

from typing import List
from typing import Literal
from typing import Optional

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import status
from sqlalchemy.ext.asyncio import async_sessionmaker

from ..database import get_async_session_maker
from ..finance.dependencies import CurrentUser
from .schemas import AddressCreate
from .schemas import AssetsDTO
from .schemas import BalancesDTO
from .schemas import ManualBalances
from .schemas import OverviewDTO
from .schemas import TimeseriesDTO
from .schemas import WalletCreate
from .schemas import WalletDTO
from .schemas import WalletList
from .schemas import WalletUpdate
from .service import CryptoService
from .service import PERIOD_DAYS

crypto_router = APIRouter(
    prefix="/api/crypto",
    tags=["Crypto"],
)

Period = Literal["7d", "30d", "90d", "1y", "all"]


@crypto_router.get("/wallets", status_code=status.HTTP_200_OK, response_model=WalletList)
async def list_wallets(
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> WalletList:
    """All wallets with addresses, holdings and totals in the base currency."""
    return await CryptoService.list_for_user(user.id, session_maker)


@crypto_router.post("/wallets", status_code=status.HTTP_201_CREATED, response_model=WalletDTO)
async def create_wallet(
    schema: WalletCreate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> WalletDTO:
    return await CryptoService.create_for_user(schema, user.id, session_maker)


@crypto_router.patch("/wallets/{wallet_id}", status_code=status.HTTP_200_OK, response_model=WalletDTO)
async def update_wallet(
    wallet_id: int,
    schema: WalletUpdate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> WalletDTO:
    return await CryptoService.update_for_user(wallet_id, schema, user.id, session_maker)


@crypto_router.delete("/wallets/{wallet_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wallet(
    wallet_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> None:
    await CryptoService.delete_for_user(wallet_id, user.id, session_maker)


@crypto_router.post("/wallets/{wallet_id}/addresses", status_code=status.HTTP_201_CREATED, response_model=WalletDTO)
async def add_address(
    wallet_id: int,
    schema: AddressCreate,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> WalletDTO:
    return await CryptoService.add_address(wallet_id, schema.chain, schema.address, user.id, session_maker)


@crypto_router.delete("/wallets/{wallet_id}/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    wallet_id: int,
    address_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> None:
    await CryptoService.delete_address(wallet_id, address_id, user.id, session_maker)


@crypto_router.post("/wallets/{wallet_id}/sync", status_code=status.HTTP_200_OK, response_model=BalancesDTO)
async def sync_wallet(
    wallet_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> BalancesDTO:
    """Refresh holdings from the chain right now and return them with sync status."""
    return await CryptoService.sync_now(wallet_id, user.id, session_maker)


@crypto_router.get("/wallets/{wallet_id}/balances", status_code=status.HTTP_200_OK, response_model=BalancesDTO)
async def get_balances(
    wallet_id: int,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> BalancesDTO:
    return await CryptoService.balances(wallet_id, user.id, session_maker)


@crypto_router.put("/wallets/{wallet_id}/balances", status_code=status.HTTP_200_OK, response_model=BalancesDTO)
async def set_balances(
    wallet_id: int,
    schema: ManualBalances,
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> BalancesDTO:
    """Replace hand-entered holdings (manual/telegram wallets only)."""
    return await CryptoService.set_manual_holdings(wallet_id, schema.holdings, user.id, session_maker)


@crypto_router.get("/overview", status_code=status.HTTP_200_OK, response_model=OverviewDTO)
async def overview(
    user: CurrentUser,
    period: Period = Query("30d"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> OverviewDTO:
    return await CryptoService.overview(user.id, period, session_maker)


@crypto_router.get("/timeseries", status_code=status.HTTP_200_OK, response_model=TimeseriesDTO)
async def timeseries(
    user: CurrentUser,
    period: Period = Query("30d"),
    group_by: Literal["total", "asset", "wallet"] = Query("total"),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> TimeseriesDTO:
    return await CryptoService.timeseries(user.id, period, group_by, session_maker)


@crypto_router.get("/assets", status_code=status.HTTP_200_OK, response_model=AssetsDTO)
async def assets(
    user: CurrentUser,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> AssetsDTO:
    """Distinct asset codes across the user's wallets (manual-mode asset picker)."""
    return AssetsDTO(assets=await CryptoService.asset_codes(user.id, session_maker))
