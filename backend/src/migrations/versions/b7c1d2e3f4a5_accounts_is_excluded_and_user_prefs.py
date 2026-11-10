"""accounts.is_excluded and user profile preferences

Revision ID: b7c1d2e3f4a5
Revises: 7c1f0a9b2d34
Create Date: 2026-11-02 00:40:00.000000

Three fields are needed by the frontend:

* ``accounts.is_excluded`` — "Exclude from statistics" toggle: the account and its
  transactions stay in place, but totals, charts and analytics do not count them;
* ``users.base_currency`` — currency in which the user views totals;
* ``users.locale`` and ``users.theme`` — interface preferences so a new device
  opens in the same language and theme as the previous one.

``base_currency`` intentionally has no foreign key to ``currencies``: the currency
catalog lives in finance and is populated by a separate migration, and the user must
be created independently of seed order.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b7c1d2e3f4a5"
down_revision = "7c1f0a9b2d34"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "accounts",
        sa.Column(
            "is_excluded", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "base_currency", sa.String(length=3), nullable=True, server_default="BYN"
        ),
    )
    op.add_column(
        "users",
        sa.Column("locale", sa.String(length=8), nullable=True, server_default="ru"),
    )
    op.add_column(
        "users",
        sa.Column(
            "theme", sa.String(length=16), nullable=True, server_default="system"
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "theme")
    op.drop_column("users", "locale")
    op.drop_column("users", "base_currency")
    op.drop_column("accounts", "is_excluded")
