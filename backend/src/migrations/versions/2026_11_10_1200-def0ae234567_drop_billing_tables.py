"""Drop billing tables: the application is now fully free and open-source.

Revision ID: def0ae234567
Revises: c9d0e1f2a3b4
Create Date: 2026-11-10 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "def0ae234567"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None

BILLING_TABLES = [
    "payments",
    "payment_methods",
    "plan_subscriptions",
    "plans",
]


def upgrade():
    for table in BILLING_TABLES:
        op.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')


def downgrade():
    # Billing is gone for good; restoring it requires the historical
    # f1a2b3c4d5e6 migration code or a fresh redesign.
    raise NotImplementedError("Billing has been removed from the project")
