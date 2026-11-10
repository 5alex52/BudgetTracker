import uuid
from datetime import datetime
from enum import Enum
from typing import Any
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class AccountType(str, Enum):
    CASH = "cash"
    CHECKING = "checking"
    CREDIT_CARD = "credit_card"
    SAVINGS = "savings"
    INVESTMENT = "investment"


class CategoryType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class RuleField(str, Enum):
    """What the rule condition applies to."""

    NOTE = "note"
    AMOUNT = "amount"


class RuleOperator(str, Enum):
    """How to compare the condition value."""

    CONTAINS = "contains"
    EQUALS = "equals"
    GREATER = "greater"
    LESS = "less"


class SubscriptionFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class AccountBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: AccountType
    currency_id: str = Field(..., min_length=3, max_length=3)
    # Negative balances are valid (credit cards, overdrafts)
    balance: float = Field(default=0.0)
    is_archived: bool = False
    #: Account excluded from statistics (totals, charts, analytics)
    is_excluded: bool = False

    model_config = ConfigDict(from_attributes=True)


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[AccountType] = None
    currency_id: Optional[str] = Field(None, min_length=3, max_length=3)
    balance: Optional[float] = None
    is_archived: Optional[bool] = None
    is_excluded: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class AccountResponse(AccountBase):
    id: int
    user_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None


class AccountInline(BaseModel):
    id: int
    name: str
    type: AccountType
    currency_id: str
    balance: float
    is_archived: bool
    is_excluded: bool = False

    model_config = ConfigDict(from_attributes=True)


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: CategoryType
    parent_id: Optional[int] = None
    icon: Optional[str] = Field("category", max_length=255)
    color: Optional[str] = Field("#6366f1", max_length=20)

    model_config = ConfigDict(from_attributes=True)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[CategoryType] = None
    parent_id: Optional[int] = None
    icon: Optional[str] = Field(None, max_length=255)
    color: Optional[str] = Field(None, max_length=20)

    model_config = ConfigDict(from_attributes=True)


class CategoryResponse(CategoryBase):
    id: int
    user_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None


class CategoryInline(BaseModel):
    id: int
    name: str
    type: CategoryType
    icon: Optional[str]
    color: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class TagInline(BaseModel):
    """Tag in a transaction response."""

    id: int
    name: str
    color: str

    model_config = ConfigDict(from_attributes=True)


class TransactionBase(BaseModel):
    account_id: int
    #: Transfers have no category: the server substitutes the service "Transfer" category
    category_id: Optional[int] = None
    #: Transfer destination account; only for type=transfer
    transfer_account_id: Optional[int] = None
    amount: float = Field(..., gt=0)
    currency_id: str = Field(..., min_length=3, max_length=3)
    type: TransactionType
    date: datetime
    note: Optional[str] = Field(None, max_length=500)
    is_subscription: bool = False
    receipt_url: Optional[str] = Field(None, max_length=255)
    #: Tags to attach to the record
    tag_ids: List[int] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    transfer_account_id: Optional[int] = None
    amount: Optional[float] = Field(None, gt=0)
    currency_id: Optional[str] = Field(None, min_length=3, max_length=3)
    type: Optional[TransactionType] = None
    date: Optional[datetime] = None
    note: Optional[str] = Field(None, max_length=500)
    is_subscription: Optional[bool] = None
    receipt_url: Optional[str] = Field(None, max_length=255)
    tag_ids: Optional[List[int]] = None

    model_config = ConfigDict(from_attributes=True)


class TransactionResponse(TransactionBase):
    id: int
    created_at: datetime
    #: Hidden from statistics by a rule
    is_excluded: bool = False
    tags: List["TagInline"] = Field(default_factory=list)


class TransactionWithDetails(TransactionResponse):
    account_name: str
    category_name: str
    category_color: str
    category_icon: str
    currency_symbol: str
    #: Name of the transfer destination account
    transfer_account_name: Optional[str] = None

    @classmethod
    def from_model(cls, transaction: Any) -> "TransactionWithDetails":
        """Builds a detailed representation from a transaction ORM instance.

        Related account, category and currency objects have to be loaded already
        (the DAO queries use eager loading for them).
        """
        data = TransactionResponse.model_validate(transaction).model_dump()
        return cls(
            **data,
            account_name=transaction.account.name,
            category_name=transaction.category.name,
            category_color=transaction.category.color,
            category_icon=transaction.category.icon,
            currency_symbol=transaction.currency.symbol,
            transfer_account_name=(
                transaction.transfer_account.name if transaction.transfer_account is not None else None
            ),
        )


class CategoryTotal(BaseModel):
    category_id: int
    name: str
    color: str
    icon: str
    total: float
    transactions_count: int


class TransactionSummary(BaseModel):
    total: float
    transactions_count: int
    by_category: List[CategoryTotal] = Field(default_factory=list)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class BalanceOverviewAccount(BaseModel):
    """Account balance at end of period: in its own currency and in the base."""

    account_id: int
    name: str
    currency_id: str
    balance: float
    balance_base: float
    is_archived: bool = False
    is_excluded: bool = False


class BalanceOverview(BaseModel):
    """User's overall balance.

    ``total`` and ``balance_base`` are already converted to the user's base
    currency using current (including personal) rates: balances of different
    currencies must not be added on the client.
    """

    total: float
    accounts: List[BalanceOverviewAccount] = Field(default_factory=list)


class SubscriptionBase(BaseModel):
    frequency: SubscriptionFrequency
    next_payment_date: datetime
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class SubscriptionCreate(SubscriptionBase):
    transaction_id: int


class SubscriptionUpdate(BaseModel):
    frequency: Optional[SubscriptionFrequency] = None
    next_payment_date: Optional[datetime] = None
    is_active: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class SubscriptionResponse(SubscriptionBase):
    id: int
    transaction_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None


class CurrencyBase(BaseModel):
    code: str = Field(..., min_length=3, max_length=3)
    name: str = Field(..., min_length=1, max_length=255)
    symbol: str = Field(default="$", max_length=10)

    model_config = ConfigDict(from_attributes=True)


class CurrencyCreate(CurrencyBase):
    exchange_rate_to_base: float = Field(default=1.0, gt=0)


class CurrencyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    symbol: Optional[str] = Field(None, max_length=10)
    exchange_rate_to_base: Optional[float] = Field(None, gt=0)

    model_config = ConfigDict(from_attributes=True)


class CurrencyResponse(CurrencyBase):
    exchange_rate_to_base: float
    last_updated: Optional[datetime] = None


# --------------------------------------------------------------------------- #
#  Additional views for frontend screens
# --------------------------------------------------------------------------- #


class AccountSummary(BaseModel):
    """Account card: balance and turnover for the period."""

    account_id: int
    name: str
    currency_id: str
    balance: float
    is_archived: bool = False
    is_excluded: bool = False
    income: float
    expense: float
    net: float
    transactions_count: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class CategoryNode(BaseModel):
    """Category with subcategories — a tree for settings and the transaction dialog."""

    id: int
    name: str
    type: CategoryType
    parent_id: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    transactions_count: int = 0
    children: List["CategoryNode"] = Field(default_factory=list)


CategoryNode.model_rebuild()


class CategoryStat(BaseModel):
    """Category row: how many records and what total."""

    category_id: int
    name: str
    type: CategoryType
    parent_id: Optional[int] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    transactions_count: int
    total: float


class BulkDeleteResult(BaseModel):
    """Bulk delete result: what was deleted and what was not found."""

    deleted: int
    missing: List[int] = Field(default_factory=list)


class BulkDeleteRequest(BaseModel):
    ids: List[int] = Field(..., min_length=1, max_length=500)


class CurrencyRate(BaseModel):
    """Currency rate relative to the chosen base: how many units per 1 base unit."""

    code: str
    name: str
    symbol: str
    rate: float
    is_base: bool = False
    #: Rate overridden by the user (personal), not taken from the catalog
    is_custom: bool = False


# --------------------------------------------------------------------------- #
#  Tags, templates, rules, personal rates
# --------------------------------------------------------------------------- #


class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    color: str = Field("#6366f1", max_length=20)

    model_config = ConfigDict(from_attributes=True)


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    color: Optional[str] = Field(None, max_length=20)


class TagResponse(TagBase):
    id: int
    #: How many records are tagged — the frontend shows this next to the tag
    transactions_count: int = 0


class TemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: TransactionType
    amount: float = Field(..., gt=0)
    currency_id: str = Field(..., min_length=3, max_length=3)
    account_id: int
    category_id: int
    note: Optional[str] = Field(None, max_length=500)
    icon: str = Field("bolt", max_length=255)

    model_config = ConfigDict(from_attributes=True)


class TemplateCreate(TemplateBase):
    tag_ids: List[int] = Field(default_factory=list)


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[TransactionType] = None
    amount: Optional[float] = Field(None, gt=0)
    currency_id: Optional[str] = Field(None, min_length=3, max_length=3)
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    note: Optional[str] = Field(None, max_length=500)
    icon: Optional[str] = Field(None, max_length=255)
    tag_ids: Optional[List[int]] = None


class TemplateResponse(TemplateBase):
    id: int
    usage_count: int = 0
    tags: List[TagInline] = Field(default_factory=list)


class RuleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True
    priority: int = Field(100, ge=0, le=1000)
    field: RuleField
    operator: RuleOperator
    value: str = Field(..., min_length=1, max_length=255)
    set_category_id: Optional[int] = None
    add_tag_id: Optional[int] = None
    exclude_from_statistics: bool = False

    model_config = ConfigDict(from_attributes=True)


class RuleCreate(RuleBase):
    pass


class RuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=0, le=1000)
    field: Optional[RuleField] = None
    operator: Optional[RuleOperator] = None
    value: Optional[str] = Field(None, min_length=1, max_length=255)
    set_category_id: Optional[int] = None
    add_tag_id: Optional[int] = None
    exclude_from_statistics: Optional[bool] = None


class RuleResponse(RuleBase):
    id: int
    category_name: Optional[str] = None
    tag_name: Optional[str] = None


class RuleApplyResult(BaseModel):
    """What the rules engine did: matched rules and modified records."""

    matched_rules: List[int] = Field(default_factory=list)
    updated_transactions: int = 0
    dry_run: bool = False


class UserCurrencyRateUpdate(BaseModel):
    rate: float = Field(..., gt=0)


class TransactionDetails(TransactionWithDetails):
    """Record with details and tags — response for the edit dialog."""

    tags: List[TagInline] = Field(default_factory=list)

    @classmethod
    def from_model(cls, transaction: Any) -> "TransactionDetails":
        data = TransactionWithDetails.from_model(transaction).model_dump()
        return cls(**data)


TransactionResponse.model_rebuild()
TemplateResponse.model_rebuild()
