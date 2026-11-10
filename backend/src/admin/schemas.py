"""Admin panel schemas: users and user statistics."""

import uuid
from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field


class AdminUser(BaseModel):
    """User in the admin list."""

    id: uuid.UUID
    fullname: str
    email: str
    is_active: bool
    is_verified: bool
    is_superuser: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None


class AdminUserPage(BaseModel):
    items: List[AdminUser]
    total: int
    offset: int
    limit: int


class AdminUserUpdate(BaseModel):
    """What an admin can change in another user's account."""

    firstname: Optional[str] = Field(None, max_length=255)
    lastname: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, max_length=255)
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class AdminStats(BaseModel):
    users_total: int
    users_new_30d: int
