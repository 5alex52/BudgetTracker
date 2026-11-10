"""Fix plan features: array instead of JSON string

The previous migration stored the features list as a serialized string.
The `json` column held a string, not an array, causing `/billing/plans`
to fail schema validation. Here the string is expanded into a real JSON array.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-06 14:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # JSON string → array: `#>> '{}'` extracts the text, cast yields json
    op.execute(
        sa.text(
            "UPDATE plans SET features = (features #>> '{}')::json "
            "WHERE json_typeof(features) = 'string'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE plans SET features = to_json(features::text)::json "
            "WHERE json_typeof(features) = 'array'"
        )
    )
