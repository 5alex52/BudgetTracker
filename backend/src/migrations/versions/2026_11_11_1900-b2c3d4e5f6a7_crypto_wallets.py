"""Crypto wallet tracker: wallets, addresses, holdings, snapshots, prices, sync runs.

Read-only tracking of public addresses (EVM/BTC/TON/TRON) plus hand-entered
manual wallets, daily balance history and a global CoinGecko price cache.

Revision ID: b2c3d4e5f6a7
Revises: e8b1d3f5a7c9
Create Date: 2026-11-11 19:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "e8b1d3f5a7c9"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "crypto_wallets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("trust", "telegram", "manual", name="crypto_wallet_kind"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("crypto_wallets_user_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("crypto_wallets_pkey")),
    )
    op.create_index(op.f("crypto_wallets_id_idx"), "crypto_wallets", ["id"], unique=False)
    op.create_index(op.f("crypto_wallets_user_id_idx"), "crypto_wallets", ["user_id"], unique=False)

    op.create_table(
        "crypto_addresses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column(
            "chain",
            sa.Enum("evm", "btc", "ton", "tron", name="crypto_chain"),
            nullable=False,
        ),
        sa.Column("address", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["crypto_wallets.id"],
            name=op.f("crypto_addresses_wallet_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("crypto_addresses_pkey")),
        sa.UniqueConstraint("wallet_id", "chain", "address", name="uq_crypto_addresses_wallet_chain_address"),
    )
    op.create_index(op.f("crypto_addresses_id_idx"), "crypto_addresses", ["id"], unique=False)
    op.create_index(op.f("crypto_addresses_wallet_id_idx"), "crypto_addresses", ["wallet_id"], unique=False)

    op.create_table(
        "crypto_holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column("asset_code", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(38, 18), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["crypto_wallets.id"],
            name=op.f("crypto_holdings_wallet_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("crypto_holdings_pkey")),
        sa.UniqueConstraint("wallet_id", "asset_code", name="uq_crypto_holdings_wallet_asset"),
    )
    op.create_index(op.f("crypto_holdings_id_idx"), "crypto_holdings", ["id"], unique=False)
    op.create_index(op.f("crypto_holdings_wallet_id_idx"), "crypto_holdings", ["wallet_id"], unique=False)

    op.create_table(
        "crypto_balance_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column("asset_code", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(38, 18), nullable=False),
        sa.Column("price_usd", sa.Numeric(24, 12), nullable=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("taken_at", sa.DateTime(), nullable=False),
        sa.Column(
            "source",
            sa.Enum("backfill", "scheduler", "manual", name="crypto_snapshot_source"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["crypto_wallets.id"],
            name=op.f("crypto_balance_snapshots_wallet_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("crypto_balance_snapshots_pkey")),
        sa.UniqueConstraint("wallet_id", "asset_code", "day", name="uq_crypto_balance_snapshots_wallet_asset_day"),
    )
    op.create_index(op.f("crypto_balance_snapshots_id_idx"), "crypto_balance_snapshots", ["id"], unique=False)
    op.create_index(
        op.f("crypto_balance_snapshots_wallet_id_idx"), "crypto_balance_snapshots", ["wallet_id"], unique=False
    )
    op.create_index(
        "ix_crypto_balance_snapshots_wallet_asset_day",
        "crypto_balance_snapshots",
        ["wallet_id", "asset_code", "day"],
        unique=False,
    )

    op.create_table(
        "crypto_price_daily",
        sa.Column("asset_code", sa.String(length=16), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("price_usd", sa.Numeric(24, 12), nullable=False),
        sa.PrimaryKeyConstraint("asset_code", "day", name="uq_crypto_price_daily_asset_day"),
    )

    op.create_table(
        "crypto_sync_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("wallet_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ok", "error", "partial", name="crypto_sync_status"),
            nullable=False,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["wallet_id"],
            ["crypto_wallets.id"],
            name=op.f("crypto_sync_runs_wallet_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("crypto_sync_runs_pkey")),
    )
    op.create_index(op.f("crypto_sync_runs_id_idx"), "crypto_sync_runs", ["id"], unique=False)
    op.create_index(op.f("crypto_sync_runs_wallet_id_idx"), "crypto_sync_runs", ["wallet_id"], unique=False)


def downgrade():
    op.drop_table("crypto_sync_runs")
    op.drop_table("crypto_price_daily")
    op.drop_table("crypto_balance_snapshots")
    op.drop_table("crypto_holdings")
    op.drop_table("crypto_addresses")
    op.drop_table("crypto_wallets")
    sa.Enum(name="crypto_sync_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="crypto_snapshot_source").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="crypto_chain").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="crypto_wallet_kind").drop(op.get_bind(), checkfirst=True)
