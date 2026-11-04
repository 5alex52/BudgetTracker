"""Новые цены тарифов: 1.99 за месяц и 19.99 за год

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-11-04 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE plans SET price = 1.99 WHERE code = 'monthly'"))
    op.execute(sa.text("UPDATE plans SET price = 19.99 WHERE code = 'yearly'"))


def downgrade() -> None:
    op.execute(sa.text("UPDATE plans SET price = 4.99 WHERE code = 'monthly'"))
    op.execute(sa.text("UPDATE plans SET price = 49.99 WHERE code = 'yearly'"))
