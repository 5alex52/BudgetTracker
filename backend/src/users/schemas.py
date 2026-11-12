import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator


class UserBase(BaseModel):
    firstname: Optional[str] = Field(None)
    lastname: Optional[str] = Field(None)
    email: Optional[str] = Field(None)
    telegram_id: Optional[int] = Field(None)
    photo: Optional[str] = Field(None)
    git_username: Optional[str] = Field(None)
    is_active: bool = Field(True)
    is_verified: bool = Field(False)
    is_superuser: bool = Field(False)
    timezone: Optional[str] = Field("Europe/Minsk")
    base_currency: Optional[str] = Field("BYN")
    locale: Optional[str] = Field("ru")
    theme: Optional[str] = Field("system")
    default_period: Optional[str] = Field("month")

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    firstname: str
    lastname: str
    email: str
    password: str
    timezone: Optional[str] = Field(None)
    git_username: Optional[str] = Field(None)


class UserUpdate(UserBase):
    password: Optional[str] = Field(None)


class UserProfileUpdate(BaseModel):
    """Edit own profile from Settings.

    Privileges are intentionally absent here: `is_superuser`, `is_active`, and
    `is_verified` are not changed through the profile, otherwise the user could
    grant themselves elevated rights.
    """

    firstname: Optional[str] = Field(None, min_length=1, max_length=255)
    lastname: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    photo: Optional[str] = Field(None, max_length=2048)
    timezone: Optional[str] = Field(None, max_length=64)
    base_currency: Optional[str] = Field(None, min_length=3, max_length=3)
    locale: Optional[str] = Field(None, max_length=8)
    #: How many days before a subscription charge the reminder is sent: 0 = same day, 1 (default) = day before, 2 = two days before
    reminder_days_before: Optional[int] = Field(None, ge=0, le=2)
    theme: Optional[str] = Field(None, max_length=16)
    default_period: Optional[str] = Field(None, max_length=8)

    @field_validator("email")
    @classmethod
    def _check_email(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and "@" not in value:
            raise ValueError("Invalid email address")
        return value

    @field_validator("theme")
    @classmethod
    def _check_theme(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in {"system", "light", "dark"}:
            raise ValueError("theme must be one of: system, light, dark")
        return value

    @field_validator("default_period")
    @classmethod
    def _check_default_period(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and value not in {"day", "week", "month"}:
            raise ValueError("default_period must be one of: day, week, month")
        return value


class PasswordChange(BaseModel):
    """Change password: current password is required."""

    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class AccountDeleteConfirmation(BaseModel):
    """Confirm account deletion with a password."""

    password: str = Field(..., min_length=1)


class UserExport(BaseModel):
    """User data archive for "Download my data"."""

    user: "User"
    exported_at: datetime
    accounts: list = Field(default_factory=list)
    categories: list = Field(default_factory=list)
    transactions: list = Field(default_factory=list)
    subscriptions: list = Field(default_factory=list)
    currencies: list = Field(default_factory=list)


class User(UserBase):
    id: uuid.UUID
    fullname: str
    email: str
    #: Not all users have Telegram linked: email registration doesn't fill it in
    telegram_id: Optional[int] = None
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime]
    last_login_at: Optional[datetime]
    timezone: Optional[str]
    photo: Optional[str]
    git_username: Optional[str]
    base_currency: Optional[str] = None
    locale: Optional[str] = None
    theme: Optional[str] = None
    default_period: Optional[str] = None
    #: 0 = remind on the charge day, 1 = day before (default), 2 = two days before
    reminder_days_before: Optional[int] = None


class TelegramLinkInfo(BaseModel):
    """How to link the Telegram bot: code to send as /start and the deep link."""

    code: str
    bot_username: Optional[str] = None
    deep_link: Optional[str] = None
    chat_id: Optional[int] = None


class PushSubscribeRequest(BaseModel):
    """Browser Web Push subscription from PushManager.subscribe()."""

    endpoint: str = Field(..., max_length=1024)
    keys: "PushKeys"


class PushKeys(BaseModel):
    p256dh: str = Field(..., max_length=256)
    auth: str = Field(..., max_length=256)


class PushPublicKeyResponse(BaseModel):
    public_key: str


class PushEndpointRequest(BaseModel):
    """Unsubscribe only needs the endpoint."""

    endpoint: str = Field(..., max_length=1024)


class UserInline(BaseModel):
    id: uuid.UUID
    fullname: str
    photo: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class RefreshSessionBase(BaseModel):
    refresh_token: uuid.UUID
    expires_in: int


class RefreshSessionCreate(RefreshSessionBase):
    user_id: uuid.UUID
    device_name: str
    device_type: str


class Token(BaseModel):
    access_token: str
    refresh_token: uuid.UUID
    token_type: str


class DeviceInfo(BaseModel):
    device_name: str
    device_type: str
    last_login: datetime


class SessionInfo(BaseModel):
    device_name: str
    device_type: str
    last_login: datetime
    refresh_token: uuid.UUID


UserExport.model_rebuild()
PushSubscribeRequest.model_rebuild()
