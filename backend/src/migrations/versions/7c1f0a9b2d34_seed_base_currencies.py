"""seed base currencies

Revision ID: 7c1f0a9b2d34
Revises: eaca08a294fc
Create Date: 2026-11-01 23:10:00.000000

The currency catalog must exist before accounts are created: accounts.currency_id
and transactions.currency_id reference it. Without currencies the app cannot
create a single account, so the initial currency set is seeded by a migration.
"""

from datetime import datetime
from datetime import timezone

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7c1f0a9b2d34"
down_revision = "eaca08a294fc"
branch_labels = None
depends_on = None


# (code, name, symbol, rate to base currency)
BASE_CURRENCIES = [
    ("USD", "US Dollar", "$", 1.0),
    ("EUR", "Euro", "€", 1.08),
    ("GBP", "British Pound", "£", 1.27),
    ("CHF", "Swiss Franc", "CHF", 1.13),
    ("JPY", "Japanese Yen", "¥", 0.0064),
    ("CNY", "Chinese Yuan", "¥", 0.14),
    ("RUB", "Russian Ruble", "₽", 0.011),
    ("KZT", "Kazakhstani Tenge", "₸", 0.0022),
    ("UAH", "Ukrainian Hryvnia", "₴", 0.024),
    ("BYN", "Belarusian Ruble", "Br", 0.31),
    ("TRY", "Turkish Lira", "₺", 0.029),
    ("PLN", "Polish Zloty", "zł", 0.25),
    ("CAD", "Canadian Dollar", "C$", 0.73),
    ("AUD", "Australian Dollar", "A$", 0.66),
]

currencies = sa.table(
    "currencies",
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("symbol", sa.String),
    sa.column("exchange_rate_to_base", sa.Float),
    sa.column("last_updated", sa.DateTime),
)


def upgrade() -> None:
    connection = op.get_bind()
    existing = {code for (code,) in connection.execute(sa.text("SELECT code FROM currencies"))}
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    rows = [
        {
            "code": code,
            "name": name,
            "symbol": symbol,
            "exchange_rate_to_base": rate,
            "last_updated": now,
        }
        for code, name, symbol, rate in BASE_CURRENCIES
        if code not in existing
    ]

    if rows:
        op.bulk_insert(currencies, rows)


def downgrade() -> None:
    codes = [code for code, *_ in BASE_CURRENCIES]
    op.execute(currencies.delete().where(currencies.c.code.in_(codes)))
