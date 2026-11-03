"""Починка features у тарифов: массив вместо JSON-строки

Предыдущая миграция записала список возможностей сериализованной строкой.
Колонка `json` хранила строку, а не массив, из-за чего ответ `/billing/plans`
падал на валидации схемы. Здесь строка разворачивается в настоящий JSON-массив.

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
    # Строка JSON → массив: `#>> '{}'` достаёт текст, приведение даёт json
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
