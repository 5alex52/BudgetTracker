"""Request/response models and enums for the crypto wallet tracker."""

import enum
from datetime import date
from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class WalletKind(str, enum.Enum):
    """trust = watch a public address; telegram/manual = amounts entered by hand."""

    TRUST = "trust"
    TELEGRAM = "telegram"
    MANUAL = "manual"


class Chain(str, enum.Enum):
    EVM = "evm"
    BTC = "btc"
    TON = "ton"
    TRON = "tron"
    SOLANA = "solana"
    AVALANCHE = "avalanche"


class SnapshotSource(str, enum.Enum):
    BACKFILL = "backfill"
    SCHEDULER = "scheduler"
    MANUAL = "manual"


class SyncStatus(str, enum.Enum):
    OK = "ok"
    ERROR = "error"
    PARTIAL = "partial"


class AddressIn(BaseModel):
    chain: Chain
    address: str = Field(..., min_length=16, max_length=128)


class AddressCreate(BaseModel):
    chain: Chain
    address: str = Field(..., min_length=16, max_length=128)


class AddressDTO(BaseModel):
    id: int
    chain: Chain
    address: str
    is_active: bool


class HoldingIn(BaseModel):
    asset_code: str = Field(..., min_length=2, max_length=16)
    amount: float = Field(..., ge=0)


class HoldingDTO(BaseModel):
    asset_code: str
    amount: float
    price_usd: Optional[float] = None
    value_usd: Optional[float] = None
    value_base: Optional[float] = None


class WalletCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    kind: WalletKind = WalletKind.TRUST
    addresses: Optional[List[AddressIn]] = None
    #: Only used by manual/telegram wallets: assets the user enters himself
    holdings: Optional[List[HoldingIn]] = None


class WalletUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)


class ManualBalances(BaseModel):
    holdings: List[HoldingIn]


class WalletDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: WalletKind
    addresses: List[AddressDTO]
    holdings: List[HoldingDTO]
    total_usd: float
    total_base: float
    base_currency: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    #: Latest crypto_sync_runs row for this wallet
    last_sync_status: Optional[str] = None
    last_sync_at: Optional[datetime] = None


class WalletList(BaseModel):
    items: List[WalletDTO]
    total_usd: float
    total_base: float
    base_currency: str


class BalancesDTO(BaseModel):
    wallet_id: int
    #: Result of the last sync ("ok" | "error" | "partial"); None on plain reads
    status: Optional[str] = None
    holdings: List[HoldingDTO]
    total_usd: float
    total_base: float
    base_currency: str


class AssetBreakdown(BaseModel):
    asset_code: str
    amount: float
    price_usd: Optional[float] = None
    value_base: float
    change_percent: Optional[float] = None


class WalletBreakdown(BaseModel):
    wallet_id: int
    name: str
    value_base: float
    change_percent: Optional[float] = None


class OverviewDTO(BaseModel):
    period: str
    base_currency: str
    total_now_base: float
    change_absolute: float
    change_percent: Optional[float] = None
    by_asset: List[AssetBreakdown]
    by_wallet: List[WalletBreakdown]


class TimeseriesPoint(BaseModel):
    day: date
    total_base: float
    by_asset: dict[str, float]
    by_wallet: dict[str, float]


class TimeseriesDTO(BaseModel):
    period: str
    group_by: str
    base_currency: str
    points: List[TimeseriesPoint]


class AssetsDTO(BaseModel):
    assets: List[str]
