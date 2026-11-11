"""Visible automatic billing rule per service subscription.

Revision ID: c3d5e7f9a1b3
Revises: b2e4f6a8c0d2
Create Date: 2026-11-11 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "c3d5e7f9a1b3"
down_revision = "b2e4f6a8c0d2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "service_sub_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("service_sub_id", sa.Integer(), nullable=False),
        sa.Column(
            "frequency",
            postgresql.ENUM("daily", "weekly", "monthly", "yearly", name="subscription_frequency", create_type=False),
            nullable=False,
        ),
        sa.Column("next_payment_date", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["service_sub_id"], ["service_subscriptions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("service_sub_id"),
    )
    op.create_index(op.f("service_sub_rules_id_idx"), "service_sub_rules", ["id"])
    op.create_index(op.f("service_sub_rules_service_sub_id_idx"), "service_sub_rules", ["service_sub_id"])
    op.create_index(op.f("service_sub_rules_next_payment_date_idx"), "service_sub_rules", ["next_payment_date"])


def downgrade():
    op.drop_index(op.f("service_sub_rules_next_payment_date_idx"), table_name="service_sub_rules")
    op.drop_index(op.f("service_sub_rules_service_sub_id_idx"), table_name="service_sub_rules")
    op.drop_index(op.f("service_sub_rules_id_idx"), table_name="service_sub_rules")
    op.drop_table("service_sub_rules")
