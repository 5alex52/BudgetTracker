"""Backfill automatic billing rules for existing service subscriptions.

Subscriptions created before the auto-rule feature have no rule row. Create a
monthly rule for every subscription that already has a charging account, using
its current schedule watermark (or start date). Idempotent: skips subscriptions
that already have a rule.

Revision ID: d4e6f8a0c2b4
Revises: c3d5e7f9a1b3
Create Date: 2026-11-11 15:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d4e6f8a0c2b4"
down_revision = "c3d5e7f9a1b3"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        INSERT INTO service_sub_rules (service_sub_id, frequency, next_payment_date, is_active, created_at)
        SELECT s.id, 'monthly', COALESCE(s.next_payment_date, s.started_at), TRUE, now()
        FROM service_subscriptions s
        WHERE s.account_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM service_sub_rules r WHERE r.service_sub_id = s.id
          )
        """)


def downgrade():
    # Rules are real data once created; a backfill cannot be cleanly undone
    # without knowing which rows it added. Leave them in place.
    pass
