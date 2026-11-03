import logging
import random
import uuid

import pytest
import pytest_asyncio
from faker import Faker
from fakeredis.aioredis import FakeRedis
from fastapi import FastAPI
from httpx import ASGITransport
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from src.database import Base
from src.database import get_async_session_maker
from src.database import settings
from src.finance.schemas import AccountCreate
from src.finance.schemas import AccountType
from src.finance.schemas import CategoryCreate
from src.finance.schemas import CategoryType
from src.finance.schemas import CurrencyCreate
from src.finance.service import AccountService
from src.finance.service import CategoryService
from src.finance.service import CurrencyService
from src.main import app
from src.users.models import UserModel
from src.users.schemas import UserCreate
from src.users.service import UserService

logger = logging.getLogger()

fake = Faker()


@pytest_asyncio.fixture
async def currencies(session_maker) -> dict:
    """Базовый справочник валют: нужен и финансам, и профилю (выгрузка, базовая валюта)"""
    await CurrencyService.create(
        CurrencyCreate(
            code="USD", name="US Dollar", symbol="$", exchange_rate_to_base=1.0
        ),
        session_maker=session_maker,
    )
    await CurrencyService.create(
        CurrencyCreate(
            code="EUR", name="Euro", symbol="EUR", exchange_rate_to_base=1.1
        ),
        session_maker=session_maker,
    )
    return {"USD": 1.0, "EUR": 1.1}


@pytest.fixture
def user_info() -> UserCreate:
    """Создаёт валидные данные нового пользователя для тестов"""
    return UserCreate(
        firstname=fake.first_name(),
        lastname=fake.last_name(),
        email=fake.unique.email(),
        password=fake.password(length=16),
        telegram_id=fake.random_int(min=10_000_000, max=99_999_999),
        photo=fake.url(),
        git_username=fake.user_name(),
        is_active=True,
        is_verified=False,
        is_superuser=False,
        timezone="Europe/Minsk",
    )


@pytest_asyncio.fixture(scope="session")
async def redis_client():
    """Создает фейковый Redis клиент для тестов"""
    fake_redis = FakeRedis(decode_responses=True)
    UserService.verification_redis = fake_redis
    yield fake_redis
    await fake_redis.aclose()


@pytest_asyncio.fixture(scope="session")
async def test_db():
    try:
        """Создаёт тестовую БД и применяет к ней все миграции"""
        root_engine = create_async_engine(
            settings.ASYNC_TEST_DATABASE_URL,
            echo=False,
            future=True,
            isolation_level="AUTOCOMMIT",
        )

        name = f"TEST_{random.randint(1, 1000)}"

        async with root_engine.connect() as conn:
            await conn.execute(text(f'CREATE DATABASE "{name}"'))

        yield settings.create_ASYNC_TEST_DATABASE_URL(name)

    except Exception as e:
        logger.error(f"Ошибка при создании и удалении тестовой БД: {e}")
        raise e
    finally:
        async with root_engine.connect() as conn:
            await conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE);'))
        await root_engine.dispose()


@pytest_asyncio.fixture
async def session_maker(test_db, redis_client):
    """Создаёт session_maker для тестов и очищает соединения после тестов"""
    logger.info("Инициализация тестовой базы данных и Redis")
    test_engine = create_async_engine(test_db, echo=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

        try:
            await redis_client.ping()
            logger.info("Успешное подключение к тестовому Redis")
        except Exception as e:
            logger.error(f"Ошибка подключения к тестовому Redis: {e}")

    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    yield test_session_maker

    await test_engine.dispose()


@pytest_asyncio.fixture
def test_app(session_maker):
    """
    Создает тестовое приложение FastAPI с переопределенной зависимостью для session_maker
    """

    async def get_test_session():
        return session_maker

    app.dependency_overrides[get_async_session_maker] = get_test_session

    return app


@pytest_asyncio.fixture
async def async_client(test_app: FastAPI):
    """
    Создает асинхронный клиент для тестирования эндпоинтов
    """
    async with AsyncClient(
        transport=ASGITransport(test_app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def verified_user_client(
    async_client: AsyncClient, user_info: UserCreate, session_maker
) -> tuple[AsyncClient, uuid.UUID, str]:
    """Фикстура создает верифицированного пользователя и возвращает клиент с токеном"""
    # Создаем пользователя
    response = await async_client.post(
        "/api/auth/register", json=user_info.model_dump()
    )
    assert response.status_code == 201
    user_id = response.json()["id"]

    # Получаем токен верификации
    keys = await UserService.verification_redis.keys("email_verification:*")
    for key in keys:
        value = await UserService.verification_redis.get(key)
        if value == str(user_id):
            token = key.split(":")[1]
            break

    # Верифицируем email
    response = await async_client.post(
        "/api/auth/verify-email", params={"token": token}
    )
    assert response.status_code == 200

    # Логинимся
    login_response = await async_client.post(
        "/api/auth/login",
        data={
            "username": user_info.email,
            "password": user_info.password,
            "grant_type": "password",
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        },
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]
    refresh_token = login_response.json()["refresh_token"]

    user = await UserService.get(user_id, session_maker)
    assert user is not None
    assert user.is_verified is True

    async_client.cookies["access_token"] = access_token
    async_client.cookies["refresh_token"] = refresh_token
    return async_client, user.id, refresh_token


# --- Финансовые фикстуры: общие для finance, analytics и billing ---

BASE_TEST_URL = "http://localhost:8000"
fake = Faker()


async def create_user(session_maker) -> UserModel:
    """Создаёт подтверждённого пользователя напрямую через сервис"""
    user_info = UserCreate(
        firstname=fake.first_name(),
        lastname=fake.last_name(),
        email=fake.unique.email(),
        password=fake.password(length=16),
        telegram_id=fake.random_int(min=10_000_000, max=99_999_999),
        timezone="Europe/Minsk",
    )
    return await UserService.create(
        user_info, base_url=BASE_TEST_URL, session_maker=session_maker
    )


@pytest_asyncio.fixture
async def user(user_info: UserCreate, session_maker) -> UserModel:
    """Пользователь, которому принадлежат финансовые данные в тестах"""
    return await UserService.create(
        user_info, base_url=BASE_TEST_URL, session_maker=session_maker
    )


@pytest_asyncio.fixture
async def other_user(session_maker) -> UserModel:
    """Второй пользователь для проверки изоляции данных"""
    return await create_user(session_maker)


@pytest_asyncio.fixture
async def account(user, currencies, session_maker):
    """Счет в долларах с начальным балансом"""
    return await AccountService.create_for_user(
        schema=AccountCreate(
            name="Cash", type=AccountType.CASH, currency_id="USD", balance=1000.0
        ),
        user_id=user.id,
        session_maker=session_maker,
    )


@pytest_asyncio.fixture
async def second_account(user, currencies, session_maker):
    """Второй счет пользователя, используется в тестах переводов"""
    return await AccountService.create_for_user(
        schema=AccountCreate(
            name="Savings", type=AccountType.SAVINGS, currency_id="USD", balance=500.0
        ),
        user_id=user.id,
        session_maker=session_maker,
    )


@pytest_asyncio.fixture
async def expense_category(user, session_maker):
    """Категория расходов"""
    return await CategoryService.create_for_user(
        schema=CategoryCreate(name="Groceries", type=CategoryType.EXPENSE),
        user_id=user.id,
        session_maker=session_maker,
    )


@pytest_asyncio.fixture
async def income_category(user, session_maker):
    """Категория доходов"""
    return await CategoryService.create_for_user(
        schema=CategoryCreate(name="Salary", type=CategoryType.INCOME),
        user_id=user.id,
        session_maker=session_maker,
    )
