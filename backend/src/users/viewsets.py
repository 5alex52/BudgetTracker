import uuid
from typing import Optional

from fastapi import Depends
from fastapi import HTTPException
from fastapi import Request
from fastapi import Response
from fastapi import status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.config import settings
from src.database import get_async_session_maker
from src.users.permissions import UserPermission
from src.users.schemas import AccountDeleteConfirmation
from src.users.schemas import PasswordChange
from src.users.schemas import SessionInfo
from src.users.schemas import Token
from src.users.schemas import User
from src.users.schemas import UserCreate
from src.users.schemas import UserExport
from src.users.schemas import UserProfileUpdate
from src.users.schemas import DeviceInfo
from src.users.schemas import UserUpdate
from src.users.service import AuthService
from src.users.service import UserService
from src.users.utils import get_device_info
from src.viewset import BaseViewSet
from src.viewset import check_permissions


class UserViewSet(BaseViewSet[uuid.UUID, UserCreate, UserUpdate]):
    permission = UserPermission
    service = UserService

    @classmethod
    @check_permissions(action="create")
    async def create(
        cls,
        obj_data: UserCreate,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> User:
        obj_data.is_verified = False
        obj_data.is_active = True
        obj_data.is_superuser = False
        return await super().create(obj_data=obj_data, session_maker=session_maker, **kwargs)

    @classmethod
    @check_permissions(action="get_profile")
    async def get_profile(
        cls,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> User:
        return await cls.service.get_profile(user_id=user.id, session_maker=session_maker)

    @classmethod
    @check_permissions(action="update_profile")
    async def update_profile(
        cls,
        obj_data: UserProfileUpdate,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> User:
        return await cls.service.update_profile(user_id=user.id, schema=obj_data, session_maker=session_maker)

    @classmethod
    @check_permissions(action="change_password")
    async def change_password(
        cls,
        obj_data: PasswordChange,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> None:
        await cls.service.change_password(user_id=user.id, schema=obj_data, session_maker=session_maker)

    @classmethod
    @check_permissions(action="export_data")
    async def export_data(
        cls,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> UserExport:
        return await cls.service.export_data(user_id=user.id, session_maker=session_maker)

    @classmethod
    @check_permissions(action="delete_own_account")
    async def delete_own_account(
        cls,
        obj_data: AccountDeleteConfirmation,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
        **kwargs,
    ) -> None:
        await cls.service.delete_own_account(user_id=user.id, schema=obj_data, session_maker=session_maker)

    @classmethod
    @check_permissions(action="send_verification_email")
    async def send_verification_email(
        cls,
        user_email: str,
        request: Request,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
    ) -> dict:
        return await cls.service.send_verification_email(user_email, request.base_url, session_maker)

    @classmethod
    @check_permissions(action="verify_email")
    async def verify_email(
        cls,
        token: str,
        device_info: DeviceInfo = None,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
    ) -> Optional[Token]:
        result = await UserService.verify_email(token, session_maker, device_info)
        return result


class AuthViewSet(BaseViewSet[uuid.UUID, UserCreate, UserUpdate]):
    permission = UserPermission
    service = AuthService

    @classmethod
    @check_permissions(action="login")
    async def login(
        cls,
        request: Request,
        response: Response,
        credentials: OAuth2PasswordRequestForm,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
    ) -> Token:
        device_info = get_device_info(request.headers.get("User-Agent"))
        token = await cls.service.login(
            credentials=credentials,
            device_info=device_info,
            session_maker=session_maker,
        )
        response.set_cookie(
            "access_token",
            token.access_token,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            httponly=True,
            secure=settings.ENVIRONMENT != "LOCAL",
            samesite="strict",
        )
        response.set_cookie(
            "refresh_token",
            token.refresh_token,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            httponly=True,
            secure=settings.ENVIRONMENT != "LOCAL",
            samesite="strict",
        )
        return token

    @classmethod
    @check_permissions(action="logout")
    async def logout(
        cls,
        user: User,
        request: Request,
        response: Response,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
    ) -> dict:
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        await cls.service.logout(request.cookies.get("refresh_token"), session_maker)
        return {"message": "Logged out successfully"}

    @classmethod
    @check_permissions(action="refresh")
    async def refresh(
        cls,
        request: Request,
        response: Response,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
    ) -> Token:
        refresh_token = request.cookies.get("refresh_token")
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token not found",
            )
        new_token = await cls.service.refresh_token(uuid.UUID(refresh_token), session_maker)

        response.set_cookie(
            "access_token",
            new_token.access_token,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            httponly=True,
            secure=settings.ENVIRONMENT != "LOCAL",
            samesite="strict",
        )
        response.set_cookie(
            "refresh_token",
            new_token.refresh_token,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            httponly=True,
            secure=settings.ENVIRONMENT != "LOCAL",
            samesite="strict",
        )
        return new_token

    @classmethod
    @check_permissions(action="abort")
    async def abort(
        cls,
        user: User,
        response: Response,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
    ) -> dict:
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        await cls.service.abort_all_sessions(user.id, session_maker)
        return {"message": "All sessions was aborted"}

    @classmethod
    @check_permissions(action="sessions")
    async def sessions(
        cls,
        user: User,
        session_maker: async_sessionmaker = Depends(get_async_session_maker),
    ) -> list[SessionInfo]:
        return await cls.service.get_user_sessions(user.id, session_maker)
