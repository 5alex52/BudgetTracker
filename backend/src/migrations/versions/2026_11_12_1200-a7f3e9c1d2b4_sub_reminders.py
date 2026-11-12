"""Subscription charge reminders: user prefs, push subscriptions, dedup log.

Revision ID: a7f3e9c1d2b4
Revises: d5e6f7a8b9c0
Create Date: 2026-11-12 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "a7f3e9c1d2b4"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("reminder_days_before", sa.SmallInteger(), nullable=False, server_default="1"),
    )
    op.add_column("users", sa.Column("telegram_link_code", sa.String(16), nullable=True))
    op.create_index("ix_users_telegram_link_code", "users", ["telegram_link_code"], unique=True)
    op.create_unique_constraint("uq_users_telegram_link_code", "users", ["telegram_link_code"])

    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("user_id", UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_push_subscriptions_endpoint", "push_subscriptions", ["endpoint"], unique=True)
    op.create_unique_constraint("uq_push_subscriptions_endpoint", "push_subscriptions", ["endpoint"])

    op.create_table(
        "service_sub_reminders",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "service_sub_id",
            sa.Integer(),
            sa.ForeignKey("service_subscriptions.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        ),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("service_sub_id", "due_date", name="uq_sub_reminder_once"),
    )


def downgrade() -> None:
    op.drop_table("service_sub_reminders")
    op.drop_constraint("uq_push_subscriptions_endpoint", "push_subscriptions", type_="unique")
    op.drop_index("ix_push_subscriptions_endpoint", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")
    op.drop_constraint("uq_users_telegram_link_code", "users", type_="unique")
    op.drop_index("ix_users_telegram_link_code", table_name="users")
    op.drop_column("users", "telegram_link_code")
    op.drop_column("users", "reminder_days_before")
