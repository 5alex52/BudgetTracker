"""Default reporting period in user profile

Revision ID: e5f6a7b8c9d0
Revises: d3e4f5a6b7c8
Create Date: 2026-11-06 13:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d3e4f5a6b7c8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("default_period", sa.String(length=8), nullable=True, server_default="month"),
    )


def downgrade() -> None:
    op.drop_column("users", "default_period")
