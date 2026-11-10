"""tags, templates, rules and per-user currency rates

Revision ID: ecc55b6d008f
Revises: b7c1d2e3f4a5
Create Date: 2026-11-02 19:24:41.586026

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "ecc55b6d008f"
down_revision = "b7c1d2e3f4a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("color", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("tags_user_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("tags_pkey")),
        sa.UniqueConstraint("user_id", "name", name="uq_tags_user_name"),
    )
    op.create_index(op.f("tags_id_idx"), "tags", ["id"], unique=False)
    op.create_index(op.f("tags_user_id_idx"), "tags", ["user_id"], unique=False)

    op.create_table(
        "user_currency_rates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["code"], ["currencies.code"], name=op.f("user_currency_rates_code_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("user_currency_rates_user_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("user_currency_rates_pkey")),
        sa.UniqueConstraint("user_id", "code", name="uq_user_currency_rates_user_code"),
    )
    op.create_index(
        op.f("user_currency_rates_id_idx"), "user_currency_rates", ["id"], unique=False
    )
    op.create_index(
        op.f("user_currency_rates_user_id_idx"),
        "user_currency_rates",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column(
            "field", sa.Enum("note", "amount", name="rule_field"), nullable=False
        ),
        sa.Column(
            "operator",
            sa.Enum("contains", "equals", "greater", "less", name="rule_operator"),
            nullable=False,
        ),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("set_category_id", sa.Integer(), nullable=True),
        sa.Column("add_tag_id", sa.Integer(), nullable=True),
        sa.Column("exclude_from_statistics", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["add_tag_id"],
            ["tags.id"],
            name=op.f("rules_add_tag_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["set_category_id"],
            ["categories.id"],
            name=op.f("rules_set_category_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("rules_user_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("rules_pkey")),
    )
    op.create_index(op.f("rules_id_idx"), "rules", ["id"], unique=False)
    op.create_index(op.f("rules_user_id_idx"), "rules", ["user_id"], unique=False)

    op.create_table(
        "templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        # The transaction_type enum is already created by the transactions table:
        # create_type=False, otherwise Postgres will raise an error trying to create it twice
        sa.Column(
            "type",
            postgresql.ENUM(
                "income",
                "expense",
                "transfer",
                name="transaction_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency_id", sa.String(length=3), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(length=255), nullable=False),
        sa.Column("usage_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["accounts.id"],
            name=op.f("templates_account_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"], ["categories.id"], name=op.f("templates_category_id_fkey")
        ),
        sa.ForeignKeyConstraint(
            ["currency_id"],
            ["currencies.code"],
            name=op.f("templates_currency_id_fkey"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("templates_user_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("templates_pkey")),
    )
    op.create_index(op.f("templates_id_idx"), "templates", ["id"], unique=False)
    op.create_index(
        op.f("templates_user_id_idx"), "templates", ["user_id"], unique=False
    )

    op.create_table(
        "template_tags",
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name=op.f("template_tags_tag_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["templates.id"],
            name=op.f("template_tags_template_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "template_id", "tag_id", name=op.f("template_tags_pkey")
        ),
    )

    op.create_table(
        "transaction_tags",
        sa.Column("transaction_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["tag_id"],
            ["tags.id"],
            name=op.f("transaction_tags_tag_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["transactions.id"],
            name=op.f("transaction_tags_transaction_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "transaction_id", "tag_id", name=op.f("transaction_tags_pkey")
        ),
    )

    # server_default is required: the table already has rows, and adding a NOT NULL column without a default would fail
    op.add_column(
        "transactions",
        sa.Column(
            "is_excluded", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )


def downgrade() -> None:
    op.drop_column("transactions", "is_excluded")
    op.drop_table("transaction_tags")
    op.drop_table("template_tags")
    op.drop_index(op.f("templates_user_id_idx"), table_name="templates")
    op.drop_index(op.f("templates_id_idx"), table_name="templates")
    op.drop_table("templates")
    op.drop_index(op.f("rules_user_id_idx"), table_name="rules")
    op.drop_index(op.f("rules_id_idx"), table_name="rules")
    op.drop_table("rules")
    op.drop_index(
        op.f("user_currency_rates_user_id_idx"), table_name="user_currency_rates"
    )
    op.drop_index(op.f("user_currency_rates_id_idx"), table_name="user_currency_rates")
    op.drop_table("user_currency_rates")
    op.drop_index(op.f("tags_user_id_idx"), table_name="tags")
    op.drop_index(op.f("tags_id_idx"), table_name="tags")
    op.drop_table("tags")
    # Postgres doesn't drop enum types when tables are dropped: without this, re-running
    # upgrade would fail with 'type already exists'
    for enum_name in ("rule_field", "rule_operator"):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
