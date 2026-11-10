import logging
import uuid
from typing import List
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import Query
from fastapi import Request
from fastapi import Response
from fastapi import status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.database import get_async_session_maker

from .dependencies import get_current_active_user
from .dependencies import get_current_superuser
from .schemas import AccountDeleteConfirmation
from .schemas import PasswordChange
from .schemas import SessionInfo
from .schemas import Token
from .schemas import User
from .schemas import UserCreate
from .schemas import UserExport
from .utils import get_device_info
from .schemas import UserProfileUpdate
from .schemas import UserUpdate
from .viewsets import AuthViewSet
from .viewsets import UserViewSet

#: OAuth providers: client IDs and authorization URLs. Keys come from settings.
OAUTH_PROVIDERS = {
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "scope": "openid email profile",
        "id_setting": "OAUTH_GOOGLE_CLIENT_ID",
    },
    "yandex": {
        "authorize": "https://oauth.yandex.ru/authorize",
        "scope": "login:email login:info",
        "id_setting": "OAUTH_YANDEX_CLIENT_ID",
    },
    "github": {
        "authorize": "https://github.com/login/oauth/authorize",
        "scope": "read:user user:email",
        "id_setting": "OAUTH_GITHUB_CLIENT_ID",
    },
}


users_router = APIRouter(prefix="/api/users", tags=["Users"])
auth_router = APIRouter(prefix="/api/auth", tags=["auth"])


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> User:
    return await UserViewSet.create(
        request=request,
        obj_data=user_data,
        session_maker=session_maker,
        base_url=request.base_url,
    )


@auth_router.post("/login")
async def login(
    request: Request,
    response: Response,
    credentials: OAuth2PasswordRequestForm = Depends(),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Token:
    return await AuthViewSet.login(
        request=request,
        response=response,
        credentials=credentials,
        session_maker=session_maker,
    )


@auth_router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
):
    return await AuthViewSet.logout(
        user=user, request=request, response=response, session_maker=session_maker
    )


@auth_router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Token:
    return await AuthViewSet.refresh(
        request=request, response=response, session_maker=session_maker
    )


@auth_router.get("/sessions")
async def get_user_sessions(
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[SessionInfo]:
    return await AuthViewSet.sessions(user=user, session_maker=session_maker)


@auth_router.post("/abort")
async def abort_all_sessions(
    response: Response,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
):
    return await AuthViewSet.abort(
        user=user, response=response, session_maker=session_maker
    )


@auth_router.get("/oauth/{provider}")
async def oauth_start(provider: str, request: Request):
    """Start sign-in via an external service.

    Until keys are issued, the endpoint returns 503 with a clear message:
    the button stays in the UI, but the user sees the reason instead of a
    blank page. Once keys appear in settings, the redirect will work on its own.
    """
    from fastapi.responses import RedirectResponse

    from src.config import settings

    spec = OAUTH_PROVIDERS.get(provider)
    if spec is None:
        raise HTTPException(status_code=404, detail="Unknown OAuth provider")

    client_id = getattr(settings, spec["id_setting"], "")
    if not client_id:
        raise HTTPException(
            status_code=503,
            detail=f"{provider.capitalize()} sign-in is not configured yet",
        )

    redirect_uri = f"{request.base_url}api/auth/oauth/{provider}/callback"
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": spec["scope"],
        }
    )
    return RedirectResponse(url=f"{spec['authorize']}?{query}")


@auth_router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, code: Optional[str] = None):
    """Exchange code for profile and sign-in.

    Handler is a placeholder: once keys are available, this will exchange
    ``code`` for a provider token and find/create the user.
    """
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown OAuth provider")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is missing")
    raise HTTPException(
        status_code=503,
        detail=f"{provider.capitalize()} sign-in is not configured yet",
    )


@auth_router.post("/send-verification-email")
async def verify(
    request: Request,
    user_email: str,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
):
    return await UserViewSet.send_verification_email(
        user_email=user_email, request=request, session_maker=session_maker
    )


@auth_router.post("/verify-email")
async def verify_email(
    request: Request,
    response: Response,
    token: str = Query(...),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> dict:
    """Email address verification with automatic login"""
    user_agent = request.headers.get("User-Agent")
    device_info = None
    if user_agent:
        try:
            device_info = get_device_info(user_agent)
        except HTTPException:
            # Invalid User-Agent: just skip the auto-login token
            pass
    result = await UserViewSet.verify_email(
        token=token, session_maker=session_maker, device_info=device_info
    )
    if result is not None:
        # Set cookies for automatic login
        response.set_cookie(
            "access_token",
            result.access_token,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            httponly=True,
            secure=settings.ENVIRONMENT != "LOCAL",
            samesite="strict",
        )
        response.set_cookie(
            "refresh_token",
            result.refresh_token,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            httponly=True,
            secure=settings.ENVIRONMENT != "LOCAL",
            samesite="strict",
        )
        return {"message": "Email verified and logged in"}
    return {"message": "Email verified"}


@users_router.get("/", status_code=status.HTTP_200_OK)
async def get_list(
    user: User = Depends(get_current_superuser),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> List[User]:
    return await UserViewSet.list(user=user, session_maker=session_maker)


@users_router.get("/me", status_code=status.HTTP_200_OK)
async def get_me(
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> User:
    """Current user: who is logged in, for header and settings page."""
    return await UserViewSet.get_profile(user=user, session_maker=session_maker)


@users_router.patch("/me", status_code=status.HTTP_200_OK)
async def update_me(
    user_data: UserProfileUpdate,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> User:
    """Edit own profile: name, email, photo, timezone, language, base currency, theme."""
    return await UserViewSet.update_profile(
        obj_data=user_data, user=user, session_maker=session_maker
    )


@users_router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    payload: PasswordChange,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    """Change password with current password verification."""
    await UserViewSet.change_password(
        obj_data=payload, user=user, session_maker=session_maker
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.get("/me/export", status_code=status.HTTP_200_OK)
async def export_my_data(
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> UserExport:
    """Export all user data as a single JSON — "Download my data"."""
    return await UserViewSet.export_data(user=user, session_maker=session_maker)


@users_router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    payload: AccountDeleteConfirmation,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    """Delete account along with financial data (password required)."""
    await UserViewSet.delete_own_account(
        obj_data=payload, user=user, session_maker=session_maker
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.get("/{user_id}", status_code=status.HTTP_200_OK)
async def get_one(
    user_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> User:
    return await UserViewSet.retrieve(
        user=user, session_maker=session_maker, obj_id=user_id
    )


@users_router.patch("/{user_id}", status_code=status.HTTP_200_OK)
async def update(
    user_id: uuid.UUID,
    user_data: UserUpdate,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> User:
    return await UserViewSet.update(
        user=user, session_maker=session_maker, obj_id=user_id, obj_data=user_data
    )


@users_router.delete("/{user_id}")
async def delete(
    user_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    await UserViewSet.delete(user=user, session_maker=session_maker, obj_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
