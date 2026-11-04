"""transactions.transfer_account_id

Revision ID: c9d0e1f2a3b4
Revises: a1b2c3d4e5f6
Create Date: 2026-11-04 00:00:00.000000

A transfer between accounts is stored as a single record: ``account_id`` is the source,
``transfer_account_id`` is the destination. A separate transaction for the recipient is
not created, so analytics continues to exclude transfers by type.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c9d0e1f2a3b4"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("transfer_account_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_transactions_transfer_account_id_accounts",
        "transactions",
        "accounts",
        ["transfer_account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_transactions_transfer_account_id",
        "transactions",
        ["transfer_account_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_transfer_account_id", table_name="transactions")
    op.drop_constraint(
        "fk_transactions_transfer_account_id_accounts",
        "transactions",
        type_="foreignkey",
    )
    op.drop_column("transactions", "transfer_account_id")
