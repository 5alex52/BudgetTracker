"""account sort_order for user-defined display order

Revision ID: b8a1c2d3e4f5
Revises: c92179ff7f32
Create Date: 2026-11-14 00:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "b8a1c2d3e4f5"
down_revision = "c92179ff7f32"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
    )
    # Backfill: keep the current display order (creation order) stable for existing users.
    op.execute(
        "UPDATE accounts SET sort_order = sub.rn FROM "
        "(SELECT id, row_number() OVER (PARTITION BY user_id ORDER BY id) AS rn FROM accounts) AS sub "
        "WHERE accounts.id = sub.id"
    )


def downgrade() -> None:
    op.drop_column("accounts", "sort_order")
