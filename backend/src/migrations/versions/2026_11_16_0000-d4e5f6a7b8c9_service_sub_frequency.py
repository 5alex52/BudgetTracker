"""subscription frequency on the subscription itself

Revision ID: d4e5f6a7b8c9
Revises: b8a1c2d3e4f5
Create Date: 2026-11-16 00:00:00
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d4e5f6a7b8c9"
down_revision = "b8a1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "service_subscriptions",
        sa.Column(
            "frequency",
            postgresql.ENUM(
                "daily",
                "weekly",
                "monthly",
                "quarterly",
                "yearly",
                name="subscription_frequency",
                create_type=False,
            ),
            server_default="monthly",
            nullable=False,
        ),
    )
    # Backfill from the billing rule: it is the only place the period lived before.
    op.execute(
        "UPDATE service_subscriptions s SET frequency = r.frequency "
        "FROM service_sub_rules r WHERE r.service_sub_id = s.id"
    )


def downgrade() -> None:
    op.drop_column("service_subscriptions", "frequency")
