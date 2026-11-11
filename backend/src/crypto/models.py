"""Crypto wallet models: read-only watched addresses, holdings and daily snapshots."""

import uuid
from datetime import date
from datetime import datetime
from typing import List
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base
from ..users.models import UserModel
from .schemas import Chain
from .schemas import SnapshotSource
from .schemas import SyncStatus
from .schemas import WalletKind


def _enum_values(enum_cls) -> List[str]:
    """Stores enum members by their value (trust) instead of their name (TRUST)."""
    return [member.value for member in enum_cls]


class CryptoWalletModel(Base):
    __tablename__ = "crypto_wallets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(120), nullable=False)
    kind: Mapped[WalletKind] = mapped_column(
        sa.Enum(WalletKind, name="crypto_wallet_kind", values_callable=_enum_values),
        nullable=False,
    )
    #: Link to a finance account: the wallet's value then feeds main analytics balances
    account_id: Mapped[Optional[int]] = mapped_column(
        sa.Integer, sa.ForeignKey("accounts.id", ondelete="SET NULL"), index=True, nullable=True
    )
    #: Account was created together with the wallet: its balance mirrors the wallet value on sync
    account_auto_created: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=func.now(), nullable=True)

    addresses: Mapped[List["CryptoAddressModel"]] = relationship(back_populates="wallet", cascade="all, delete-orphan")
    holdings: Mapped[List["CryptoHoldingModel"]] = relationship(back_populates="wallet", cascade="all, delete-orphan")


class CryptoAddressModel(Base):
    __tablename__ = "crypto_addresses"
    __table_args__ = (
        sa.UniqueConstraint("wallet_id", "chain", "address", name="uq_crypto_addresses_wallet_chain_address"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    wallet_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("crypto_wallets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chain: Mapped[Chain] = mapped_column(
        sa.Enum(Chain, name="crypto_chain", values_callable=_enum_values), nullable=False
    )
    address: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())

    wallet: Mapped["CryptoWalletModel"] = relationship(back_populates="addresses")


class CryptoHoldingModel(Base):
    """Current state: how much of each asset the wallet holds right now."""

    __tablename__ = "crypto_holdings"
    __table_args__ = (sa.UniqueConstraint("wallet_id", "asset_code", name="uq_crypto_holdings_wallet_asset"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    wallet_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("crypto_wallets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    asset_code: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    amount: Mapped[sa.DECIMAL] = mapped_column(sa.Numeric(38, 18), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=func.now(), nullable=True)

    wallet: Mapped["CryptoWalletModel"] = relationship(back_populates="holdings")


class CryptoBalanceSnapshotModel(Base):
    """Daily point of the balance history; one row per (wallet, asset, day)."""

    __tablename__ = "crypto_balance_snapshots"
    __table_args__ = (
        sa.UniqueConstraint("wallet_id", "asset_code", "day", name="uq_crypto_balance_snapshots_wallet_asset_day"),
        sa.Index("ix_crypto_balance_snapshots_wallet_asset_day", "wallet_id", "asset_code", "day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    wallet_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("crypto_wallets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    asset_code: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    amount: Mapped[sa.DECIMAL] = mapped_column(sa.Numeric(38, 18), nullable=False)
    price_usd: Mapped[Optional[sa.DECIMAL]] = mapped_column(sa.Numeric(24, 12), nullable=True)
    day: Mapped[date] = mapped_column(sa.Date, nullable=False)
    taken_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    source: Mapped[SnapshotSource] = mapped_column(
        sa.Enum(SnapshotSource, name="crypto_snapshot_source", values_callable=_enum_values),
        nullable=False,
    )


class CryptoPriceDailyModel(Base):
    """Global (per-user-independent) cache of daily USD prices from CoinGecko."""

    __tablename__ = "crypto_price_daily"
    __table_args__ = (sa.UniqueConstraint("asset_code", "day", name="uq_crypto_price_daily_asset_day"),)

    asset_code: Mapped[str] = mapped_column(sa.String(16), primary_key=True)
    day: Mapped[date] = mapped_column(sa.Date, primary_key=True)
    price_usd: Mapped[sa.DECIMAL] = mapped_column(sa.Numeric(24, 12), nullable=False)


class CryptoSyncRunModel(Base):
    """Audit trail of one network sync attempt for a wallet."""

    __tablename__ = "crypto_sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    wallet_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("crypto_wallets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[SyncStatus] = mapped_column(
        sa.Enum(SyncStatus, name="crypto_sync_status", values_callable=_enum_values),
        nullable=False,
    )
    error: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True)
