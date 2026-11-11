"""Crypto wallets: flag accounts auto-created with the wallet.

Such an account mirrors the wallet value in its balance and is excluded from
statistics, so the linked-wallet path stays the single source in analytics.
Existing wallets (created before auto-accounts) keep the flag False.

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-11-11 22:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c4d5e6f7a8b9"
down_revision = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "crypto_wallets",
        sa.Column("account_auto_created", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_column("crypto_wallets", "account_auto_created")
