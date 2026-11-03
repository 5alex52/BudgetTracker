import logging
import uuid
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import List
from typing import Optional

from fastapi import HTTPException
from fastapi import status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.config import settings
from src.exceptions import InvalidCredentialsException
from src.exceptions import InvalidTokenException
from src.exceptions import TokenExpiredException
from src.global_utils import get_human_readable_time
from src.notifications.utils import send_notification
from src.service import BaseService

from ..database import async_session_maker as default_session_maker
from .dao import RefreshSessionDAO
from .dao import UserDAO
from .models import RefreshSessionModel
from .models import UserModel
from .schemas import AccountDeleteConfirmation
from .schemas import DeviceInfo
from .schemas import PasswordChange
from .schemas import RefreshSessionBase
from .schemas import RefreshSessionCreate
from .schemas import Token
from .schemas import UserCreate
from .schemas import UserExport
from .schemas import UserProfileUpdate
from .schemas import UserUpdate
from .utils import get_password_hash
from .utils import is_valid_password

logger = logging.getLogger(__name__)


class UserService(BaseService[UserModel, UserCreate, UserUpdate]):
    dao = UserDAO
    verification_redis: Redis
    VERIFICATION_TOKEN_EXPIRE = 24 * 60 * 60

    @classmethod
    async def create(
        cls, schema: UserCreate, base_url: str, session_maker: async_sessionmaker
    ) -> UserModel:
        schema.password = get_password_hash(schema.password)
        new_user = await super().create(schema, session_maker)
        # Стандартный набор категорий: пользователь сразу получает привычную
        # структуру расходов и доходов, а не пустой список.
        # Импорт ленивый: finance.service тянет users.dependencies, и на верхнем
        # уровне модуля это даёт циклический импорт.
        from src.finance.service import CategoryService

        await CategoryService.create_defaults_for_user(
            new_user.id, session_maker=session_maker
        )
        await cls.send_verification_email(new_user.email, base_url, session_maker)
        # Локальная среда без Redis: письмо отправить некуда, а без подтверждения
        # пользователь не попадёт в собственные данные. Сразу считаем адрес верным.
        if settings.ENVIRONMENT == "LOCAL" and not getattr(
            cls, "verification_redis", None
        ):
            async with session_maker() as session:
                await cls.dao.update(
                    session, UserModel.id == new_user.id, obj_in={"is_verified": True}
                )
                await session.commit()
        # Перечитываем пользователя, чтобы получить вычисляемые поля (fullname) и значения по умолчанию
        return await cls.get(new_user.id, session_maker)

    @classmethod
    async def get_by_email(
        cls, email: str, session_maker: async_sessionmaker = None
    ) -> Optional[UserModel]:
        """Возвращает пользователя по email или None"""
        if session_maker is None:
            session_maker = default_session_maker
        async with session_maker() as session:
            return await cls.dao.find_one_or_none(session, email=email)

    @classmethod
    async def _create_verification_token(cls, user_id: uuid.UUID) -> Optional[str]:
        """Creates verification token and saves it to Redis.

        Возвращает ``None``, если Redis недоступен: регистрация в локальной
        среде не должна падать из-за отсутствия кэша. В production отсутствие
        Redis — ошибка конфигурации, поэтому там исключение пробрасывается.
        """
        token = str(uuid.uuid4())
        if not getattr(cls, "verification_redis", None):
            if settings.ENVIRONMENT == "LOCAL":
                logger.warning("Redis is not initialized: verification email skipped")
                return None
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Redis connection not initialized",
            )

        await cls.verification_redis.set(
            f"email_verification:{token}",
            str(user_id),
            ex=cls.VERIFICATION_TOKEN_EXPIRE,
        )
        return token

    @classmethod
    async def send_verification_email(
        cls, user_email: str, base_url: str, session_maker: async_sessionmaker
    ) -> dict:
        """Sends email with verification link"""
        user = await cls.get_by_email(user_email, session_maker)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="User already verified"
            )

        token = await cls._create_verification_token(user.id)
        if token is None:
            # Redis недоступен — письмо не отправляем, но пользователь создан
            return {"message": "Verification email skipped: Redis is not initialized"}

        # Ссылка ведёт на страницу приложения, а не в API: она сама отправит
        # токен на /auth/verify-email и покажет результат.
        frontend = getattr(settings, "FRONTEND_URL", "") or base_url
        verification_url = f"{frontend.rstrip('/')}/verify-email?token={token}"

        email_template = f"""
        Hello, {user.fullname}!

        To confirm your email address, please click the link below:
        {verification_url}

        The link is valid for {get_human_readable_time(cls.VERIFICATION_TOKEN_EXPIRE, compact=True, use_days=False)}.

        Best regards,
        TrackGram Team
        """

        await send_notification(
            "email",
            user.email,
            subject="Email address confirmation",
            message=email_template,
        )
        return {"message": "Verification email sent"}

    @classmethod
    async def verify_email(cls, token: str, session_maker: async_sessionmaker) -> None:
        """Verifies email verification token and confirms user's email"""
        if not getattr(cls, "verification_redis", None):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Redis connection not initialized",
            )

        user_id = await cls.verification_redis.get(f"email_verification:{token}")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        async with session_maker() as session:
            user = await UserDAO.find_one_or_none(session, id=uuid.UUID(user_id))
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )

            user.is_verified = True
            await session.commit()
            await cls.verification_redis.delete(f"email_verification:{token}")

    @classmethod
    async def get_profile(
        cls, user_id: uuid.UUID, session_maker: async_sessionmaker
    ) -> UserModel:
        """Текущий пользователь: шапка, меню и страница настроек."""
        user = await cls.get(user_id, session_maker)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user

    @classmethod
    async def update_profile(
        cls,
        user_id: uuid.UUID,
        schema: UserProfileUpdate,
        session_maker: async_sessionmaker,
    ) -> UserModel:
        """Правка собственного профиля. Привилегии менять нельзя — их нет в схеме."""
        payload = schema.model_dump(exclude_unset=True)
        if "email" in payload:
            payload["email"] = payload["email"].lower()
            existing = await cls.get_by_email(payload["email"], session_maker)
            if existing is not None and existing.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email is already in use",
                )

        async with session_maker() as session:
            user = await UserDAO.find_one_or_none(session, id=user_id)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )
            for field, value in payload.items():
                setattr(user, field, value)
            await session.commit()
        return await cls.get(user_id, session_maker)

    @classmethod
    async def change_password(
        cls,
        user_id: uuid.UUID,
        schema: PasswordChange,
        session_maker: async_sessionmaker,
    ) -> None:
        """Меняет пароль, предварительно проверяя текущий."""
        async with session_maker() as session:
            user = await UserDAO.find_one_or_none(session, id=user_id)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )
            if not is_valid_password(schema.old_password, user.password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Wrong current password",
                )
            if schema.old_password == schema.new_password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New password must differ from the current one",
                )
            user.password = get_password_hash(schema.new_password)
            await session.commit()

    @classmethod
    async def export_data(
        cls, user_id: uuid.UUID, session_maker: async_sessionmaker
    ) -> UserExport:
        """Архив данных пользователя для «Скачать мои данные».

        Всё, что принадлежит человеку: счета, категории, записи, подписки и справочник
        валют, на который эти записи ссылаются.
        """
        from src.finance.dao import AccountDAO
        from src.finance.dao import CategoryDAO
        from src.finance.dao import CurrencyDAO
        from src.finance.dao import SubscriptionDAO
        from src.finance.dao import TransactionDAO

        user = await cls.get_profile(user_id, session_maker)
        async with session_maker() as session:
            accounts = await AccountDAO.find_all_by_user(
                session,
                user_id,
                include_archived=True,
                include_excluded=True,
                limit=1000,
            )
            categories = await CategoryDAO.find_all_by_user(
                session, user_id, limit=1000
            )
            transactions = await TransactionDAO.find_filtered(
                session, user_id, limit=5000
            )
            subscriptions = await SubscriptionDAO.find_all_by_user(
                session, user_id, limit=1000
            )
            currencies = await CurrencyDAO.find_all_ordered(session, limit=500)

        return UserExport(
            user=user,
            exported_at=datetime.now(),
            accounts=[account.as_dict() for account in accounts],
            categories=[category.as_dict() for category in categories],
            transactions=[transaction.as_dict() for transaction in transactions],
            subscriptions=[subscription.as_dict() for subscription in subscriptions],
            currencies=[currency.as_dict() for currency in currencies],
        )

    @classmethod
    async def delete_own_account(
        cls,
        user_id: uuid.UUID,
        schema: AccountDeleteConfirmation,
        session_maker: async_sessionmaker,
    ) -> None:
        """Удаление аккаунта пользователем.

        Пароль обязателен: удаление необратимо, а украденная сессия не должна
        позволять снести аккаунт одним запросом. Финансовые данные уходят
        каскадом по внешним ключам.
        """
        async with session_maker() as session:
            user = await UserDAO.find_one_or_none(session, id=user_id)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                )
            if not is_valid_password(schema.password, user.password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong password"
                )
            await UserDAO.delete(session, UserModel.id == user_id)
            await session.commit()

    @classmethod
    async def initialize_redis(cls, redis_connection: Redis) -> None:
        """Initializes Redis connection"""
        cls.verification_redis = redis_connection


class AuthService:

    @classmethod
    def _create_access_token(cls, user_id: uuid.UUID) -> str:
        to_encode = {
            "sub": str(user_id),
            "exp": datetime.now()
            + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        }
        encoded_jwt = jwt.encode(
            to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
        )
        return f"Bearer {encoded_jwt}"

    @classmethod
    def _create_refresh_token(cls) -> uuid.UUID:
        return uuid.uuid4()

    @classmethod
    async def _create_token(
        cls,
        user_id: uuid.UUID,
        device_info: DeviceInfo,
        session_maker: async_sessionmaker,
    ) -> Token:
        access_token = cls._create_access_token(user_id)
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = cls._create_refresh_token()

        async with session_maker() as session:
            await RefreshSessionDAO.create(
                session,
                RefreshSessionCreate(
                    user_id=user_id,
                    refresh_token=refresh_token,
                    expires_in=refresh_token_expires.total_seconds(),
                    device_name=device_info.device_name,
                    device_type=device_info.device_type,
                ),
            )
            await session.commit()
        return Token(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
        )

    @classmethod
    async def _authenticate_user(
        cls, email: str, password: str, session_maker: async_sessionmaker
    ) -> Optional[UserModel]:
        async with session_maker() as session:
            db_user = await UserDAO.find_one_or_none(session, email=email)
        if db_user and is_valid_password(password, db_user.password):
            return db_user
        raise InvalidCredentialsException

    @classmethod
    async def login(
        cls,
        credentials: OAuth2PasswordRequestForm,
        device_info: DeviceInfo,
        session_maker: async_sessionmaker,
    ) -> Token:
        user = await cls._authenticate_user(
            credentials.username, credentials.password, session_maker
        )
        token = await cls._create_token(user.id, device_info, session_maker)
        return token

    @classmethod
    async def logout(cls, token: uuid.UUID, session_maker: async_sessionmaker) -> None:
        async with session_maker() as session:
            refresh_session = await RefreshSessionDAO.find_one_or_none(
                session, RefreshSessionModel.refresh_token == token
            )
            if refresh_session:
                await RefreshSessionDAO.delete(session, id=refresh_session.id)
            await session.commit()

    @classmethod
    async def refresh_token(
        cls, token: uuid.UUID, session_maker: async_sessionmaker
    ) -> Token:
        async with session_maker() as session:
            refresh_session = await RefreshSessionDAO.find_one_or_none(
                session, RefreshSessionModel.refresh_token == token
            )

            if refresh_session is None:
                raise InvalidTokenException
            if datetime.now(timezone.utc) >= refresh_session.created_at + timedelta(
                seconds=refresh_session.expires_in
            ):
                await RefreshSessionDAO.delete(
                    session, RefreshSessionModel.id == refresh_session.id
                )
                raise TokenExpiredException

            user = await UserDAO.find_one_or_none(session, id=refresh_session.user_id)
            if user is None:
                raise InvalidTokenException

            access_token = cls._create_access_token(user.id)
            refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            refresh_token = cls._create_refresh_token()

            await RefreshSessionDAO.update(
                session,
                RefreshSessionModel.id == refresh_session.id,
                obj_in=RefreshSessionBase(
                    refresh_token=refresh_token,
                    expires_in=refresh_token_expires.total_seconds(),
                    last_login=datetime.now(timezone.utc),
                ),
            )
            await session.commit()
        return Token(
            access_token=access_token, refresh_token=refresh_token, token_type="bearer"
        )

    @classmethod
    async def get_user_sessions(
        cls, user_id: uuid.UUID, session_maker: async_sessionmaker
    ) -> List[RefreshSessionModel]:
        async with session_maker() as session:
            return await RefreshSessionDAO.find_all(
                session, RefreshSessionModel.user_id == user_id
            )

    @classmethod
    async def abort_all_sessions(
        cls, user_id: uuid.UUID, session_maker: async_sessionmaker
    ):
        async with session_maker() as session:
            await RefreshSessionDAO.delete_all(
                session, RefreshSessionModel.user_id == user_id
            )
            await session.commit()
