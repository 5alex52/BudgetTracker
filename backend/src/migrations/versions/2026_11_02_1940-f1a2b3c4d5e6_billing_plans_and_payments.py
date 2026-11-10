"""billing: plans, subscriptions, payment methods and payments

Revision ID: f1a2b3c4d5e6
Revises: ecc55b6d008f
Create Date: 2026-11-02 19:40:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision = "ecc55b6d008f"
branch_labels = None
depends_on = None


#: Default plans: free, monthly, and yearly
PLANS = [
    {
        "code": "free",
        "name": "Бесплатный",
        "description": "Два счёта, стандартные категории и базовые отчёты",
        "price": 0.0,
        "period": "none",
        "features": ["2 счёта", "стандартные категории", "отчёты за месяц"],
        "sort_order": 0,
    },
    {
        "code": "monthly",
        "name": "Месячный",
        "description": "Все счета, аналитика и правила",
        "price": 4.99,
        "period": "month",
        "features": [
            "неограниченно счетов",
            "несколько валют",
            "расширенная аналитика",
            "метки и правила",
            "экспорт",
        ],
        "sort_order": 1,
    },
    {
        "code": "yearly",
        "name": "Годовой",
        "description": "То же, что месячный, но со скидкой",
        "price": 49.99,
        "period": "year",
        "features": [
            "всё из месячного",
            "два месяца бесплатно",
            "приоритетная поддержка",
        ],
        "sort_order": 2,
    },
]


def upgrade() -> None:
    op.create_table(
        "plans",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "period",
            sa.Enum("none", "month", "year", name="plan_period"),
            nullable=False,
        ),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("code", name=op.f("plans_pkey")),
    )

    op.create_table(
        "plan_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("plan_code", sa.String(length=32), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "past_due",
                "canceled",
                "incomplete",
                name="subscription_status",
            ),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_reference", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["plan_code"],
            ["plans.code"],
            name=op.f("plan_subscriptions_plan_code_fkey"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("plan_subscriptions_user_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("plan_subscriptions_pkey")),
    )
    op.create_index(
        op.f("plan_subscriptions_id_idx"), "plan_subscriptions", ["id"], unique=False
    )
    op.create_index(
        op.f("plan_subscriptions_user_id_idx"),
        "plan_subscriptions",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "payment_methods",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column(
            "kind",
            sa.Enum("card", "crypto", "bank_transfer", name="payment_method_kind"),
            nullable=False,
        ),
        sa.Column("brand", sa.String(length=32), nullable=True),
        sa.Column("last4", sa.String(length=4), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("provider_reference", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("payment_methods_user_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("payment_methods_pkey")),
    )
    op.create_index(
        op.f("payment_methods_id_idx"), "payment_methods", ["id"], unique=False
    )
    op.create_index(
        op.f("payment_methods_user_id_idx"),
        "payment_methods",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=True),
        sa.Column("plan_code", sa.String(length=32), nullable=True),
        sa.Column(
            "kind",
            sa.Enum("subscription", "method_attach", name="payment_kind"),
            nullable=False,
        ),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "succeeded", "failed", "refunded", name="payment_status"
            ),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_reference", sa.String(length=255), nullable=True),
        sa.Column("failure_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["plan_subscriptions.id"],
            name=op.f("payments_subscription_id_fkey"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("payments_user_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("payments_pkey")),
    )
    op.create_index(op.f("payments_id_idx"), "payments", ["id"], unique=False)
    op.create_index(
        op.f("payments_provider_reference_idx"),
        "payments",
        ["provider_reference"],
        unique=False,
    )
    op.create_index(op.f("payments_user_id_idx"), "payments", ["user_id"], unique=False)

    # The plan catalog is needed immediately: without it the "Plans" screen is empty.
    # Column types are specified explicitly: period is an enum, otherwise the driver
    # would send VARCHAR and Postgres would refuse to cast it to plan_period.
    op.bulk_insert(
        sa.table(
            "plans",
            sa.column("code", sa.String(length=32)),
            sa.column("name", sa.String(length=255)),
            sa.column("description", sa.Text()),
            sa.column("price", sa.Float()),
            sa.column("currency", sa.String(length=3)),
            sa.column("period", postgresql.ENUM(name="plan_period", create_type=False)),
            sa.column("features", sa.JSON()),
            sa.column("is_active", sa.Boolean()),
            sa.column("sort_order", sa.Integer()),
            sa.column("created_at", sa.DateTime()),
        ),
        [
            {
                **plan,
                "currency": "USD",
                "is_active": True,
                "created_at": sa.func.now(),
            }
            for plan in PLANS
        ],
        multiinsert=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("payments_user_id_idx"), table_name="payments")
    op.drop_index(op.f("payments_provider_reference_idx"), table_name="payments")
    op.drop_index(op.f("payments_id_idx"), table_name="payments")
    op.drop_table("payments")
    op.drop_index(op.f("payment_methods_user_id_idx"), table_name="payment_methods")
    op.drop_index(op.f("payment_methods_id_idx"), table_name="payment_methods")
    op.drop_table("payment_methods")
    op.drop_index(
        op.f("plan_subscriptions_user_id_idx"), table_name="plan_subscriptions"
    )
    op.drop_index(op.f("plan_subscriptions_id_idx"), table_name="plan_subscriptions")
    op.drop_table("plan_subscriptions")
    op.drop_table("plans")
    # Postgres does not drop enum types when tables are dropped: without this,
    # a re-upgrade would fail with "type already exists"
    for enum_name in (
        "plan_period",
        "subscription_status",
        "payment_method_kind",
        "payment_kind",
        "payment_status",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
