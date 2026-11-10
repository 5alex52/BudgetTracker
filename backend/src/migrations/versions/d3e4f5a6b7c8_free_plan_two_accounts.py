"""Free plan: two accounts instead of one, paid plans have multi-currency

Revision ID: d3e4f5a6b7c8
Revises: c8d2e3f4a5b6
Create Date: 2026-11-06 12:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "d3e4f5a6b7c8"
down_revision = "c8d2e3f4a5b6"
branch_labels = None
depends_on = None

FREE_FEATURES = ["2 счёта", "стандартные категории", "отчёты за месяц"]
FREE_DESCRIPTION = "Два счёта, стандартные категории и базовые отчёты"
MONTHLY_FEATURES = [
    "неограниченно счетов",
    "несколько валют",
    "расширенная аналитика",
    "метки и правила",
    "экспорт",
]


def upgrade() -> None:
    plans = sa.table(
        "plans",
        sa.column("code", sa.String),
        sa.column("description", sa.Text),
        sa.column("features", sa.JSON),
    )
    op.execute(
        plans.update()
        .where(plans.c.code == "free")
        .values(
            description=FREE_DESCRIPTION,
            features=FREE_FEATURES,
        )
    )
    op.execute(
        plans.update()
        .where(plans.c.code == "monthly")
        .values(features=MONTHLY_FEATURES)
    )


def downgrade() -> None:
    plans = sa.table(
        "plans",
        sa.column("code", sa.String),
        sa.column("description", sa.Text),
        sa.column("features", sa.JSON),
    )
    op.execute(
        plans.update()
        .where(plans.c.code == "free")
        .values(
            description="Один счёт и базовые отчёты",
            features=["1 счёт", "5 категорий", "отчёты за месяц"],
        )
    )
    op.execute(
        plans.update()
        .where(plans.c.code == "monthly")
        .values(
            features=["неограниченно счетов", "аналитика", "метки и правила", "экспорт"]
        )
    )
