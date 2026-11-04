"""allow telegram_id to be nullable

Revision ID: c8d2e3f4a5b6
Revises: f1a2b3c4d5e6
Create Date: 2026-11-03 12:00:00.000000

Users who sign in only by email or OAuth do not have a Telegram account.
The ``telegram_id`` field is no longer required but remains unique:
two identical Telegram accounts are still forbidden.
In PostgreSQL a unique index allows multiple NULLs, so the uniqueness
constraint is preserved without additional conditions.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c8d2e3f4a5b6"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "telegram_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "telegram_id", existing_type=sa.Integer(), nullable=False)
