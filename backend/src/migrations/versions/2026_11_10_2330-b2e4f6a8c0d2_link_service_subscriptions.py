"""Link service subscriptions to accounts, categories and charge records.

Revision ID: b2e4f6a8c0d2
Revises: a7f3c1d90b21
Create Date: 2026-11-10 23:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b2e4f6a8c0d2"
down_revision = "a7f3c1d90b21"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("service_subscriptions", sa.Column("account_id", sa.Integer(), nullable=True))
    op.add_column("service_subscriptions", sa.Column("category_id", sa.Integer(), nullable=True))
    op.add_column("service_subscriptions", sa.Column("next_payment_date", sa.DateTime(), nullable=True))
    op.create_index(op.f("service_subscriptions_next_payment_date_idx"), "service_subscriptions", ["next_payment_date"])
    op.create_foreign_key(
        "fk_service_subscriptions_account",
        "service_subscriptions",
        "accounts",
        ["account_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_service_subscriptions_category",
        "service_subscriptions",
        "categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column("transactions", sa.Column("service_sub_id", sa.Integer(), nullable=True))
    op.create_index(op.f("transactions_service_sub_id_idx"), "transactions", ["service_sub_id"])
    op.create_foreign_key(
        "fk_transactions_service_sub",
        "transactions",
        "service_subscriptions",
        ["service_sub_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_transactions_service_sub", "transactions", type_="foreignkey")
    op.drop_index(op.f("transactions_service_sub_id_idx"), table_name="transactions")
    op.drop_column("transactions", "service_sub_id")
    op.drop_constraint("fk_service_subscriptions_category", "service_subscriptions", type_="foreignkey")
    op.drop_constraint("fk_service_subscriptions_account", "service_subscriptions", type_="foreignkey")
    op.drop_index(op.f("service_subscriptions_next_payment_date_idx"), table_name="service_subscriptions")
    op.drop_column("service_subscriptions", "next_payment_date")
    op.drop_column("service_subscriptions", "category_id")
    op.drop_column("service_subscriptions", "account_id")
