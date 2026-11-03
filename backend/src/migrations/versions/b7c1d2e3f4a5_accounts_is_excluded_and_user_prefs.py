"""accounts.is_excluded and user profile preferences

Revision ID: b7c1d2e3f4a5
Revises: 7c1f0a9b2d34
Create Date: 2026-11-02 00:40:00.000000

Три поля нужны фронтенду:

* ``accounts.is_excluded`` — переключатель «Исключить из статистики»: счёт и его
  операции остаются на месте, но итоги, графики и аналитика их не учитывают;
* ``users.base_currency`` — валюта, в которой пользователь смотрит итоги;
* ``users.locale`` и ``users.theme`` — предпочтения интерфейса, чтобы новое
  устройство открывалось на том же языке и в той же теме, что и прежнее.

``base_currency`` намеренно без внешнего ключа на ``currencies``: справочник
валют живёт в finance и наполняется отдельной миграцией, а пользователь должен
создаваться независимо от порядка сидов.
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
