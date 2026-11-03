"""allow telegram_id to be nullable

Revision ID: c8d2e3f4a5b6
Revises: f1a2b3c4d5e6
Create Date: 2026-11-03 12:00:00.000000

Пользователи, которые входят только по email или через OAuth, не имеют
Telegram-аккаунта. Поле ``telegram_id`` перестало быть обязательным, но
остаётся уникальным: два одинаковых Telegram-аккаунта по-прежнему запрещены.
В PostgreSQL уникальный индекс допускает несколько NULL, поэтому ограничение
на уникальность сохраняется без дополнительных условий.
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
