import uuid
from typing import Optional

from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.database import get_async_session_maker
from src.global_utils import get_token
from src.global_utils import verify_token

from .schemas import User
from .service import UserService
from .utils import OAuth2PasswordBearerWithCookie

oauth2_scheme = OAuth2PasswordBearerWithCookie(token_url="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Optional[User]:
    user_id = verify_token(token=token)
    current_user = await UserService.get(uuid.UUID(user_id), session_maker)
    if not current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not current_user.is_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verify email")
    return User.model_validate(current_user)


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough privileges")
    return current_user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not active")
    return current_user


async def get_current_active_user_optional(
    request: Request,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Optional[User]:
    """Current user or ``None`` — for endpoints that work without authentication.

    Used where the same response is enriched with personal data when a session
    exists: e.g. currency rates (catalog + personal overrides).
    """
    token = get_token(request, auto_error=False)
    if not token:
        return None
    try:
        current_user = await get_current_user(token=token, session_maker=session_maker)
        return await get_current_active_user(current_user=current_user)
    except HTTPException:
        return None
