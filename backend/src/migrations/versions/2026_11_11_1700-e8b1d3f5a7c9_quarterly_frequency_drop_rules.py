"""Quarterly subscription frequency; remove auto-categorization rules.

Adds 'quarterly' to the subscription_frequency enum and drops the obsolete
rules table (the auto-categorization feature was removed; service subscriptions
have their own billing rules in service_sub_rules).

Revision ID: e8b1d3f5a7c9
Revises: d4e6f8a0c2b4
Create Date: 2026-11-11 17:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e8b1d3f5a7c9"
down_revision = "d4e6f8a0c2b4"
branch_labels = None
depends_on = None


def upgrade():
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction block on some
    # Postgres versions; autocommit_block runs it outside the migration transaction.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE subscription_frequency ADD VALUE IF NOT EXISTS 'quarterly'")
    # Dropping the table also drops its indexes and foreign keys
    op.execute("DROP TABLE IF EXISTS rules")
    op.execute("DROP TYPE IF EXISTS rule_field")
    op.execute("DROP TYPE IF EXISTS rule_operator")


def downgrade():
    # Postgres cannot remove a value from an enum type, and the rules feature
    # is gone for good, so its table is not recreated. Nothing to undo.
    pass
