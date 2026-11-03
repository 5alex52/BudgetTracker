import logging
import uuid
from typing import List
from typing import Optional
from urllib.parse import urlencode

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
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
from .schemas import UserProfileUpdate
from .schemas import UserUpdate
from .viewsets import AuthViewSet
from .viewsets import UserViewSet

#: Провайдеры входа: клиент и адреса авторизации. Ключи — из настроек.
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
    """Начало входа через внешний сервис.

    Пока ключи не выданы, эндпоинт отвечает 503 с понятным текстом: кнопка в
    интерфейсе остаётся, но пользователь видит причину, а не «белый экран».
    Когда ключи появятся в настройках, редирект заработает сам.
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
    """Обмен кода на профиль и вход.

    Обработчик готов по месту: как только появятся ключи, здесь останется
    обменять ``code`` на токен провайдера и найти/создать пользователя.
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
    token: str,
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> dict:
    """Email address verification"""
    return await UserViewSet.verify_email(token=token, session_maker=session_maker)


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
    """Текущий пользователь: кто вошёл, для шапки и страницы настроек."""
    return await UserViewSet.get_profile(user=user, session_maker=session_maker)


@users_router.patch("/me", status_code=status.HTTP_200_OK)
async def update_me(
    user_data: UserProfileUpdate,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> User:
    """Правка своего профиля: имя, почта, фото, часовой пояс, язык, базовая валюта, тема."""
    return await UserViewSet.update_profile(
        obj_data=user_data, user=user, session_maker=session_maker
    )


@users_router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    payload: PasswordChange,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    """Смена пароля с проверкой текущего."""
    await UserViewSet.change_password(
        obj_data=payload, user=user, session_maker=session_maker
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.get("/me/export", status_code=status.HTTP_200_OK)
async def export_my_data(
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> UserExport:
    """Выгрузка всех данных пользователя одним JSON — «Скачать мои данные»."""
    return await UserViewSet.export_data(user=user, session_maker=session_maker)


@users_router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    payload: AccountDeleteConfirmation,
    user: User = Depends(get_current_active_user),
    session_maker: async_sessionmaker = Depends(get_async_session_maker),
) -> Response:
    """Удаление аккаунта вместе с финансовыми данными (требуется пароль)."""
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
