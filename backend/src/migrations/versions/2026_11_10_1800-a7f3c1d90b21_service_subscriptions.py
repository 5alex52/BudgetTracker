"""Service subscriptions tracker: table service_subscriptions.

Revision ID: a7f3c1d90b21
Revises: def0ae234567
Create Date: 2026-11-10 18:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a7f3c1d90b21"
down_revision = "def0ae234567"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "service_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("icon", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency_id", sa.String(length=3), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["currency_id"], ["currencies.code"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("service_subscriptions_id_idx"), "service_subscriptions", ["id"], unique=False)
    op.create_index(op.f("service_subscriptions_user_id_idx"), "service_subscriptions", ["user_id"], unique=False)
    op.create_index(
        op.f("service_subscriptions_currency_id_idx"), "service_subscriptions", ["currency_id"], unique=False
    )


def downgrade():
    op.drop_index(op.f("service_subscriptions_currency_id_idx"), table_name="service_subscriptions")
    op.drop_index(op.f("service_subscriptions_user_id_idx"), table_name="service_subscriptions")
    op.drop_index(op.f("service_subscriptions_id_idx"), table_name="service_subscriptions")
    op.drop_table("service_subscriptions")
