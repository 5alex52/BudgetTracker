"""Crypto account models: read-only watched addresses, holdings and daily snapshots.

A crypto wallet IS a finance account (``accounts.crypto_kind`` is set): these
tables hang off ``accounts.id`` and only exist for crypto accounts.
"""

from datetime import date
from datetime import datetime
from typing import List
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.sql import func

from ..database import Base
from .schemas import Chain
from .schemas import SnapshotSource
from .schemas import SyncStatus


def _enum_values(enum_cls) -> List[str]:
    """Stores enum members by their value (trust) instead of their name (TRUST)."""
    return [member.value for member in enum_cls]


class CryptoAddressModel(Base):
    __tablename__ = "crypto_addresses"
    __table_args__ = (
        sa.UniqueConstraint("account_id", "chain", "address", name="uq_crypto_addresses_account_chain_address"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("accounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chain: Mapped[Chain] = mapped_column(
        sa.Enum(Chain, name="crypto_chain", values_callable=_enum_values), nullable=False
    )
    address: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())


class CryptoHoldingModel(Base):
    """Current state: how much of each asset the account's wallet holds right now."""

    __tablename__ = "crypto_holdings"
    __table_args__ = (sa.UniqueConstraint("account_id", "asset_code", name="uq_crypto_holdings_account_asset"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("accounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    asset_code: Mapped[str] = mapped_column(sa.String(16), nullable=False)
    amount: Mapped[sa.DECIMAL] = mapped_column(sa.Numeric(38, 18), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=func.now(), nullable=True)


class CryptoBalanceSnapshotModel(Base):
    """Daily point of the balance history; one row per (account, asset, day)."""

    __tablename__ = "crypto_balance_snapshots"
    __table_args__ = (
        sa.UniqueConstraint("account_id", "asset_code", "day", name="uq_crypto_balance_snapshots_account_asset_day"),
        sa.Index("ix_crypto_balance_snapshots_account_asset_day", "account_id", "asset_code", "day"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("accounts.id", ondelete="CASCADE"), index=True, nullable=False
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

    asset_code: Mapped[str] = mapped_column(sa.String(16), primary_key=True)
    day: Mapped[date] = mapped_column(sa.Date, primary_key=True)
    price_usd: Mapped[sa.DECIMAL] = mapped_column(sa.Numeric(24, 12), nullable=False)


class CryptoSyncRunModel(Base):
    """Audit trail of one network sync attempt for a crypto account."""

    __tablename__ = "crypto_sync_runs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("accounts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[SyncStatus] = mapped_column(
        sa.Enum(SyncStatus, name="crypto_sync_status", values_callable=_enum_values),
        nullable=False,
    )
    error: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    finished_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime, nullable=True)
