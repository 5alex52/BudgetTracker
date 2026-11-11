"""Crypto wallet IS a finance account.

Adds accounts.crypto_kind (reuses the existing crypto_wallet_kind enum), gives
every wallet its own account row (auto-created accounts are reused and stop
being excluded), repoints crypto_addresses/holdings/snapshots/sync_runs to
account_id with cascade FKs and drops the crypto_wallets table.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-11-11 23:59:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None

# (old unique, new unique, old composite index+cols, new composite index+cols) per child table
_ADDRESSES = (
    ("uq_crypto_addresses_wallet_chain_address", ["wallet_id", "chain", "address"]),
    ("uq_crypto_addresses_account_chain_address", ["account_id", "chain", "address"]),
    None,
    None,
)
_HOLDINGS = (
    ("uq_crypto_holdings_wallet_asset", ["wallet_id", "asset_code"]),
    ("uq_crypto_holdings_account_asset", ["account_id", "asset_code"]),
    None,
    None,
)
_SNAPSHOTS = (
    ("uq_crypto_balance_snapshots_wallet_asset_day", ["wallet_id", "asset_code", "day"]),
    ("uq_crypto_balance_snapshots_account_asset_day", ["account_id", "asset_code", "day"]),
    ("ix_crypto_balance_snapshots_wallet_asset_day", ["wallet_id", "asset_code", "day"]),
    ("ix_crypto_balance_snapshots_account_asset_day", ["account_id", "asset_code", "day"]),
)
_SYNC_RUNS = (None, None, None, None)


def _repoint(table, old_uq, new_uq, old_comp, new_comp):
    """Move a crypto child table from wallet_id to account_id (wmap holds the mapping)."""
    op.add_column(table, sa.Column("account_id", sa.Integer(), nullable=True))
    op.execute(f"UPDATE {table} t SET account_id = m.account_id FROM wmap m WHERE m.wallet_id = t.wallet_id")
    op.execute(f"ALTER TABLE {table} ALTER COLUMN account_id SET NOT NULL")
    if old_uq:
        op.drop_constraint(old_uq[0], table, type_="unique")
    if old_comp:
        op.drop_index(old_comp[0], table_name=table)
    op.drop_constraint(f"{table}_wallet_id_fkey", table, type_="foreignkey")
    op.drop_index(f"{table}_wallet_id_idx", table_name=table)
    op.drop_column(table, "wallet_id")
    op.create_index(f"{table}_account_id_idx", table, ["account_id"], unique=False)
    op.create_foreign_key(f"{table}_account_id_fkey", table, "accounts", ["account_id"], ["id"], ondelete="CASCADE")
    if new_uq:
        op.create_unique_constraint(new_uq[0], table, new_uq[1])
    if new_comp:
        op.create_index(new_comp[0], table, new_comp[1], unique=False)


def _restore(table, old_uq, new_uq, old_comp, new_comp):
    """Reverse of _repoint: children key back to wallet_id (wallet ids mirror account ids)."""
    op.add_column(table, sa.Column("wallet_id", sa.Integer(), nullable=True))
    op.execute(f"UPDATE {table} t SET wallet_id = w.id FROM crypto_wallets w WHERE w.account_id = t.account_id")
    if new_uq:
        op.drop_constraint(new_uq[0], table, type_="unique")
    if new_comp:
        op.drop_index(new_comp[0], table_name=table)
    op.drop_constraint(f"{table}_account_id_fkey", table, type_="foreignkey")
    op.drop_index(f"{table}_account_id_idx", table_name=table)
    op.drop_column(table, "account_id")
    op.execute(f"ALTER TABLE {table} ALTER COLUMN wallet_id SET NOT NULL")
    op.create_index(f"{table}_wallet_id_idx", table, ["wallet_id"], unique=False)
    op.create_foreign_key(f"{table}_wallet_id_fkey", table, "crypto_wallets", ["wallet_id"], ["id"], ondelete="CASCADE")
    if old_uq:
        op.create_unique_constraint(old_uq[0], table, old_uq[1])
    if old_comp:
        op.create_index(old_comp[0], table, old_comp[1], unique=False)


def upgrade():
    op.add_column(
        "accounts",
        sa.Column(
            "crypto_kind",
            sa.Enum("trust", "telegram", "manual", name="crypto_wallet_kind", create_type=False),
            nullable=True,
        ),
    )

    # Map every wallet to its account: reuse the auto-created one, mint an account for the rest.
    op.execute("""
        CREATE TEMP TABLE wmap AS
        SELECT w.id AS wallet_id,
               CASE WHEN w.account_auto_created AND w.account_id IS NOT NULL THEN w.account_id END AS account_id
        FROM crypto_wallets w
        """)
    op.execute("""
        INSERT INTO wmap (wallet_id, account_id)
        SELECT w.id, nextval(pg_get_serial_sequence('accounts', 'id'))
        FROM crypto_wallets w
        JOIN wmap m ON m.wallet_id = w.id AND m.account_id IS NULL
        """)
    op.execute("""
        INSERT INTO accounts (id, user_id, name, type, currency_id, balance, is_archived, is_excluded,
                              crypto_kind, created_at)
        SELECT m.account_id, w.user_id, w.name, 'investment',
               CASE WHEN c.code IS NOT NULL THEN COALESCE(NULLIF(u.base_currency, ''), 'USD') ELSE 'USD' END,
               0.0, FALSE, FALSE, w.kind, now()
        FROM crypto_wallets w
        JOIN wmap m ON m.wallet_id = w.id
        LEFT JOIN users u ON u.id = w.user_id
        LEFT JOIN currencies c ON c.code = COALESCE(NULLIF(u.base_currency, ''), 'USD')
        WHERE NOT (w.account_auto_created AND w.account_id IS NOT NULL)
        """)
    op.execute("SELECT setval(pg_get_serial_sequence('accounts', 'id'), (SELECT MAX(id) FROM accounts))")
    op.execute("""
        UPDATE accounts a
        SET crypto_kind = w.kind, is_excluded = FALSE, updated_at = now()
        FROM crypto_wallets w
        WHERE w.account_id = a.id AND w.account_auto_created
        """)

    _repoint("crypto_addresses", *_ADDRESSES)
    _repoint("crypto_holdings", *_HOLDINGS)
    _repoint("crypto_balance_snapshots", *_SNAPSHOTS)
    _repoint("crypto_sync_runs", *_SYNC_RUNS)

    op.drop_table("crypto_wallets")
    op.execute("DROP TABLE wmap")


def downgrade():
    op.execute("""
        CREATE TABLE crypto_wallets (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users (id) ON DELETE CASCADE,
            name VARCHAR(120) NOT NULL,
            kind crypto_wallet_kind NOT NULL,
            account_id INTEGER REFERENCES accounts (id) ON DELETE SET NULL,
            account_auto_created BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP
        )
        """)
    op.execute("CREATE INDEX crypto_wallets_id_idx ON crypto_wallets (id)")
    op.execute("CREATE INDEX crypto_wallets_user_id_idx ON crypto_wallets (user_id)")
    op.execute("CREATE INDEX crypto_wallets_account_id_idx ON crypto_wallets (account_id)")
    # Wallet ids mirror account ids; those accounts become excluded mirrors again.
    op.execute("""
        INSERT INTO crypto_wallets (id, user_id, name, kind, account_id, account_auto_created, created_at, updated_at)
        SELECT a.id, a.user_id, a.name, a.crypto_kind, a.id, TRUE, a.created_at, a.updated_at
        FROM accounts a
        WHERE a.crypto_kind IS NOT NULL
        """)
    op.execute("UPDATE accounts SET is_excluded = TRUE WHERE crypto_kind IS NOT NULL")

    _restore("crypto_addresses", *_ADDRESSES)
    _restore("crypto_holdings", *_HOLDINGS)
    _restore("crypto_balance_snapshots", *_SNAPSHOTS)
    _restore("crypto_sync_runs", *_SYNC_RUNS)

    op.drop_column("accounts", "crypto_kind")
