"""Crypto wallets: link to a finance account; add solana and avalanche chains.

A linked wallet's value participates in the main analytics balances (total
balance and the balance time series). Deleting the account unlinks the wallet
(SET NULL), deleting the wallet never touches the account.

Revision ID: b3c4d5e6f7a8
Revises: b2c3d4e5f6a7
Create Date: 2026-11-11 21:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b3c4d5e6f7a8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block on some
    # Postgres versions; autocommit_block runs it outside the migration transaction.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE crypto_chain ADD VALUE IF NOT EXISTS 'solana'")
        op.execute("ALTER TYPE crypto_chain ADD VALUE IF NOT EXISTS 'avalanche'")
    op.add_column("crypto_wallets", sa.Column("account_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("crypto_wallets_account_id_fkey"),
        "crypto_wallets",
        "accounts",
        ["account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("crypto_wallets_account_id_idx"), "crypto_wallets", ["account_id"], unique=False)


def downgrade():
    # Postgres cannot remove a value from an enum type, so the new chains stay.
    op.drop_index(op.f("crypto_wallets_account_id_idx"), table_name="crypto_wallets")
    op.drop_constraint("crypto_wallets_account_id_fkey", "crypto_wallets", type_="foreignkey")
    op.drop_column("crypto_wallets", "account_id")
