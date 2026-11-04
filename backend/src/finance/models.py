import uuid
from datetime import datetime
from typing import List
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base
from ..users.models import UserModel
from .schemas import AccountType
from .schemas import CategoryType
from .schemas import RuleField
from .schemas import RuleOperator
from .schemas import SubscriptionFrequency
from .schemas import TransactionType


def _enum_values(enum_cls) -> List[str]:
    """Stores enum members by their value (income) instead of their name (INCOME)."""
    return [member.value for member in enum_cls]


class CurrencyModel(Base):
    __tablename__ = "currencies"

    code: Mapped[str] = mapped_column(sa.String(3), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    symbol: Mapped[str] = mapped_column(sa.String(10), default="$", nullable=False)
    exchange_rate_to_base: Mapped[float] = mapped_column(sa.Float, default=1.0, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now(), onupdate=func.now())

    accounts: Mapped[List["AccountModel"]] = relationship("AccountModel", back_populates="currency")
    transactions: Mapped[List["TransactionModel"]] = relationship("TransactionModel", back_populates="currency")


class AccountModel(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    type: Mapped[AccountType] = mapped_column(
        sa.Enum(AccountType, name="account_type", values_callable=_enum_values),
        nullable=False,
    )
    currency_id: Mapped[str] = mapped_column(sa.String(3), sa.ForeignKey("currencies.code"), index=True, nullable=False)
    balance: Mapped[float] = mapped_column(sa.Float, default=0.0, nullable=False)
    is_archived: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    #: Excluded from statistics: account lives on, operations are visible, but it does not affect totals or charts
    is_excluded: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=func.now(), nullable=True)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="accounts")
    currency: Mapped["CurrencyModel"] = relationship("CurrencyModel", back_populates="accounts", lazy="joined")
    transactions: Mapped[List["TransactionModel"]] = relationship(
        "TransactionModel",
        back_populates="account",
        cascade="all, delete-orphan",
        foreign_keys="TransactionModel.account_id",
    )


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(sa.Integer, sa.ForeignKey("categories.id"), nullable=True)
    type: Mapped[CategoryType] = mapped_column(
        sa.Enum(CategoryType, name="category_type", values_callable=_enum_values),
        nullable=False,
    )
    icon: Mapped[str] = mapped_column(sa.String(255), default="category", nullable=False)
    color: Mapped[str] = mapped_column(sa.String(20), default="#6366f1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=func.now(), nullable=True)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="categories")
    parent: Mapped[Optional["CategoryModel"]] = relationship(
        "CategoryModel", remote_side=[id], back_populates="children"
    )
    children: Mapped[List["CategoryModel"]] = relationship("CategoryModel", back_populates="parent")
    transactions: Mapped[List["TransactionModel"]] = relationship("TransactionModel", back_populates="category")


class TransactionModel(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(
        sa.Integer,
        sa.ForeignKey("accounts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    category_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("categories.id"), index=True, nullable=False)
    #: Destination account for a transfer (only for type=transfer)
    transfer_account_id: Mapped[Optional[int]] = mapped_column(
        sa.Integer, sa.ForeignKey("accounts.id", ondelete="SET NULL"), index=True, nullable=True
    )
    amount: Mapped[float] = mapped_column(sa.Float, nullable=False)
    currency_id: Mapped[str] = mapped_column(sa.String(3), sa.ForeignKey("currencies.code"), index=True, nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        sa.Enum(TransactionType, name="transaction_type", values_callable=_enum_values),
        nullable=False,
    )
    date: Mapped[datetime] = mapped_column(sa.DateTime, nullable=False, index=True)
    note: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    is_subscription: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    #: Hidden from statistics by an auto-categorization rule (the record itself stays in lists)
    is_excluded: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    receipt_url: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())

    account: Mapped["AccountModel"] = relationship(
        "AccountModel", back_populates="transactions", foreign_keys=[account_id]
    )
    transfer_account: Mapped[Optional["AccountModel"]] = relationship(
        "AccountModel", foreign_keys=[transfer_account_id]
    )
    category: Mapped["CategoryModel"] = relationship("CategoryModel", back_populates="transactions", lazy="joined")
    currency: Mapped["CurrencyModel"] = relationship("CurrencyModel", back_populates="transactions", lazy="joined")
    subscription: Mapped[Optional["SubscriptionModel"]] = relationship(
        "SubscriptionModel",
        back_populates="transaction",
        uselist=False,
        cascade="all, delete-orphan",
    )
    tags: Mapped[List["TagModel"]] = relationship(
        "TagModel", secondary="transaction_tags", back_populates="transactions"
    )

    @property
    def balance_delta(self) -> float:
        """Effect of the transaction on its account balance."""
        if self.type == TransactionType.INCOME:
            return self.amount
        return -self.amount


class SubscriptionModel(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    transaction_id: Mapped[int] = mapped_column(
        sa.Integer,
        sa.ForeignKey("transactions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    frequency: Mapped[SubscriptionFrequency] = mapped_column(
        sa.Enum(
            SubscriptionFrequency,
            name="subscription_frequency",
            values_callable=_enum_values,
        ),
        nullable=False,
    )
    next_payment_date: Mapped[datetime] = mapped_column(sa.DateTime, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=func.now(), nullable=True)

    transaction: Mapped["TransactionModel"] = relationship("TransactionModel", back_populates="subscription")


#: Tags and records are related many-to-many: one purchase may appear in several collections
transaction_tags = sa.Table(
    "transaction_tags",
    Base.metadata,
    sa.Column(
        "transaction_id",
        sa.Integer,
        sa.ForeignKey("transactions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column(
        "tag_id",
        sa.Integer,
        sa.ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class TagModel(Base):
    """User tag: "vacation", "renovation", "work"."""

    __tablename__ = "tags"
    __table_args__ = (sa.UniqueConstraint("user_id", "name", name="uq_tags_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    color: Mapped[str] = mapped_column(sa.String(20), default="#6366f1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=func.now(), nullable=True)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="tags")
    transactions: Mapped[List["TransactionModel"]] = relationship(
        "TransactionModel", secondary=transaction_tags, back_populates="tags"
    )


#: Template tags: when the template is applied, these are attached to the created record
template_tags = sa.Table(
    "template_tags",
    Base.metadata,
    sa.Column(
        "template_id",
        sa.Integer,
        sa.ForeignKey("templates.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.Column(
        "tag_id",
        sa.Integer,
        sa.ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class TemplateModel(Base):
    """Quick-entry template: a pre-set record that creates a transaction."""

    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    type: Mapped[TransactionType] = mapped_column(
        sa.Enum(TransactionType, name="transaction_type", values_callable=_enum_values),
        nullable=False,
    )
    amount: Mapped[float] = mapped_column(sa.Float, nullable=False)
    currency_id: Mapped[str] = mapped_column(sa.String(3), sa.ForeignKey("currencies.code"), nullable=False)
    account_id: Mapped[int] = mapped_column(
        sa.Integer, sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    category_id: Mapped[int] = mapped_column(sa.Integer, sa.ForeignKey("categories.id"), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(sa.Text, nullable=True)
    icon: Mapped[str] = mapped_column(sa.String(255), default="bolt", nullable=False)
    #: How many times the template was used — the frontend sorts by popularity
    usage_count: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=func.now(), nullable=True)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="templates")
    tags: Mapped[List["TagModel"]] = relationship("TagModel", secondary=template_tags)


class RuleModel(Base):
    """Auto-categorization rule: a condition on a record and actions on match."""

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, default=True, nullable=False)
    #: Lower is earlier; rules are applied in ascending priority order
    priority: Mapped[int] = mapped_column(sa.Integer, default=100, nullable=False)
    field: Mapped[RuleField] = mapped_column(
        sa.Enum(RuleField, name="rule_field", values_callable=_enum_values),
        nullable=False,
    )
    operator: Mapped[RuleOperator] = mapped_column(
        sa.Enum(RuleOperator, name="rule_operator", values_callable=_enum_values),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    set_category_id: Mapped[Optional[int]] = mapped_column(
        sa.Integer, sa.ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    add_tag_id: Mapped[Optional[int]] = mapped_column(
        sa.Integer, sa.ForeignKey("tags.id", ondelete="SET NULL"), nullable=True
    )
    exclude_from_statistics: Mapped[bool] = mapped_column(sa.Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=func.now(), nullable=True)

    user: Mapped["UserModel"] = relationship("UserModel", back_populates="rules")


class UserCurrencyRateModel(Base):
    """Personal user rate: overrides the catalog rate for their calculations."""

    __tablename__ = "user_currency_rates"
    __table_args__ = (sa.UniqueConstraint("user_id", "code", name="uq_user_currency_rates_user_code"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(sa.String(3), sa.ForeignKey("currencies.code"), nullable=False)
    rate: Mapped[float] = mapped_column(sa.Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, onupdate=func.now(), nullable=True)
