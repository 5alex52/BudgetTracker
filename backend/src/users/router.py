import logging
import uuid
from datetime import datetime
from datetime import timezone
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
from src.config import settings
from src.database import get_async_session_maker

from .dependencies import get_current_active_user
from .dependencies import get_current_superuser
from .schemas import AccountDeleteConfirmation
from .schemas import PasswordChange
from .schemas import PushEndpointRequest
from .schemas import PushPublicKeyResponse
from .schemas import PushSubscribeRequest
from .schemas import SessionInfo
from .schemas import TelegramAuthRequest
from .schemas import TelegramLinkInfo
from .schemas import DeviceInfo
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


@auth_router.post("/telegram")
async def login_telegram(
    request: Request,
    response: Response,
    payload: TelegramAuthRequest,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Token:
    """Вход из Telegram Mini App по подписанным initData (без пароля)."""
    return await AuthViewSet.login_telegram(
        request=request,
        response=response,
        init_data=payload.init_data,
        session_maker=session_maker,
    )


@auth_router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
):
    return await AuthViewSet.logout(user=user, request=request, response=response, session_maker=session_maker)


@auth_router.post("/refresh")
async def refresh_token(
    request: Request,
    response: Response,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Token:
    return await AuthViewSet.refresh(request=request, response=response, session_maker=session_maker)


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
    return await AuthViewSet.abort(user=user, response=response, session_maker=session_maker)


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
async def oauth_callback(
    provider: str,
    request: Request,
    code: Optional[str] = None,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
):
    """GitHub sign-in: exchange the code, find or create the user, set cookies."""
    if provider not in OAUTH_PROVIDERS:
        raise HTTPException(status_code=404, detail="Unknown OAuth provider")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code is missing")

    import httpx
    from fastapi.responses import RedirectResponse

    from src.config import settings
    from .service import AuthService
    from .service import UserService

    client_id = settings.OAUTH_GITHUB_CLIENT_ID
    client_secret = settings.OAUTH_GITHUB_CLIENT_SECRET
    if not client_id or not client_secret:
        raise HTTPException(status_code=503, detail="GitHub sign-in is not configured yet")

    # redirect_uri is not required by GitHub's token exchange, but sending a
    # wrong one is rejected — we do not send it, the code alone identifies it.
    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            params={"client_id": client_id, "client_secret": client_secret, "code": code},
            headers={"Accept": "application/json"},
        )
        github_token = (token_response.json() or {}).get("access_token")
        if token_response.status_code != 200 or not github_token:
            raise HTTPException(status_code=401, detail="GitHub rejected the authorization code")

        gh_headers = {"Authorization": f"Bearer {github_token}", "Accept": "application/vnd.github+json"}
        profile = (await client.get("https://api.github.com/user", headers=gh_headers)).json()
        emails = (await client.get("https://api.github.com/user/emails", headers=gh_headers)).json()

    login = profile.get("login") if isinstance(profile, dict) else None
    if not login:
        raise HTTPException(status_code=401, detail="Could not read the GitHub profile")
    email = next(
        (
            (e["email"] for e in emails if isinstance(e, dict) and e.get("primary") and e.get("verified"))
            if isinstance(emails, list)
            else []
        ),
        None,
    )
    if not email:
        raise HTTPException(status_code=400, detail="GitHub account has no verified primary email")

    user = await UserService.get_by_email(email, session_maker=session_maker)
    if user is None:
        user = await UserService.create_from_oauth(
            email=email, name=profile.get("name"), git_username=login, session_maker=session_maker
        )

    user_agent = request.headers.get("User-Agent")
    try:
        device_info = get_device_info(user_agent) if user_agent else None
    except HTTPException:
        device_info = None
    if device_info is None:
        device_info = DeviceInfo(
            device_name=user_agent or "Unknown device",
            device_type="Desktop",
            last_login=datetime.now(timezone.utc),
        )

    token = await AuthService._create_token(user.id, device_info, session_maker)
    redirect = RedirectResponse(url=settings.OAUTH_RETURN_URL)
    for cookie_name, cookie_value, max_age in (
        ("access_token", token.access_token, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60),
        ("refresh_token", str(token.refresh_token), settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60),
    ):
        redirect.set_cookie(
            cookie_name,
            cookie_value,
            max_age=max_age,
            httponly=True,
            secure=settings.ENVIRONMENT != "LOCAL",
            samesite="strict",
        )
    return redirect


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
    result = await UserViewSet.verify_email(token=token, session_maker=session_maker, device_info=device_info)
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
    return await UserViewSet.update_profile(obj_data=user_data, user=user, session_maker=session_maker)


@users_router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    payload: PasswordChange,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    """Change password with current password verification."""
    await UserViewSet.change_password(obj_data=payload, user=user, session_maker=session_maker)
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
    await UserViewSet.delete_own_account(obj_data=payload, user=user, session_maker=session_maker)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.get("/me/telegram/link", status_code=status.HTTP_200_OK)
async def telegram_link(
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> TelegramLinkInfo:
    """Code + deep link for linking the Telegram bot (user sends /start <code>)."""
    return await UserViewSet.telegram_link(user=user, session_maker=session_maker)


@users_router.delete("/me/telegram", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_telegram(
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    await UserViewSet.unlink_telegram(user=user, session_maker=session_maker)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.get("/me/push/public-key", status_code=status.HTTP_200_OK)
async def push_public_key(
    user: User = Depends(get_current_active_user),
) -> PushPublicKeyResponse:
    """VAPID public key for pushManager.subscribe."""
    return PushPublicKeyResponse(public_key=settings.VAPID_PUBLIC_KEY)


@users_router.post("/me/push", status_code=status.HTTP_204_NO_CONTENT)
async def subscribe_push(
    payload: PushSubscribeRequest,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    """Store the browser's Web Push subscription."""
    await UserViewSet.subscribe_push(obj_data=payload, user=user, session_maker=session_maker)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.delete("/me/push", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_push(
    payload: PushEndpointRequest,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    await UserViewSet.unsubscribe_push(obj_data=payload, user=user, session_maker=session_maker)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.get("/{user_id}", status_code=status.HTTP_200_OK)
async def get_one(
    user_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> User:
    return await UserViewSet.retrieve(user=user, session_maker=session_maker, obj_id=user_id)


@users_router.patch("/{user_id}", status_code=status.HTTP_200_OK)
async def update(
    user_id: uuid.UUID,
    user_data: UserUpdate,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> User:
    return await UserViewSet.update(user=user, session_maker=session_maker, obj_id=user_id, obj_data=user_data)


@users_router.delete("/{user_id}")
async def delete(
    user_id: uuid.UUID,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    await UserViewSet.delete(user=user, session_maker=session_maker, obj_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
