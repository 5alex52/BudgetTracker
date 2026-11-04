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
    """Base currency catalog: needed by both finance and profile (export, base currency)"""
    await CurrencyService.create(
        CurrencyCreate(code="USD", name="US Dollar", symbol="$", exchange_rate_to_base=1.0),
        session_maker=session_maker,
    )
    await CurrencyService.create(
        CurrencyCreate(code="EUR", name="Euro", symbol="EUR", exchange_rate_to_base=1.1),
        session_maker=session_maker,
    )
    return {"USD": 1.0, "EUR": 1.1}


@pytest.fixture
def premium_entitlements(monkeypatch):
    """Enables the paid plan for tests that need multiple currencies.

    Free plan limits are tested separately; here we need to isolate analytics
    and conversion, otherwise creating an EUR account is legitimately rejected
    with HTTP 402.
    """
    from src.billing.schemas import Entitlements
    from src.billing.service import BillingService

    async def _entitlements(user_id, session_maker=None):
        return Entitlements(
            plan_code="premium",
            plan_name="Premium",
            is_paid=True,
            is_active=True,
            max_accounts=None,
            multi_currency=True,
            advanced_analytics=True,
        )

    monkeypatch.setattr(BillingService, "get_entitlements", _entitlements)


@pytest.fixture
def user_info() -> UserCreate:
    """Creates valid data for a new user for tests"""
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
    """Creates a fake Redis client for tests"""
    fake_redis = FakeRedis(decode_responses=True)
    UserService.verification_redis = fake_redis
    yield fake_redis
    await fake_redis.aclose()


@pytest_asyncio.fixture(scope="session")
async def test_db():
    try:
        """Creates a test database and applies all migrations to it"""
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
        logger.error(f"Error creating and dropping test database: {e}")
        raise e
    finally:
        async with root_engine.connect() as conn:
            await conn.execute(text(f'DROP DATABASE "{name}" WITH (FORCE);'))
        await root_engine.dispose()


@pytest_asyncio.fixture
async def session_maker(test_db, redis_client):
    """Creates a session_maker for tests and cleans up connections after tests"""
    logger.info("Initializing test database and Redis")
    test_engine = create_async_engine(test_db, echo=False)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

        try:
            await redis_client.ping()
            logger.info("Successfully connected to test Redis")
        except Exception as e:
            logger.error(f"Error connecting to test Redis: {e}")

    test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)

    yield test_session_maker

    await test_engine.dispose()


@pytest_asyncio.fixture
def test_app(session_maker):
    """
    Creates a test FastAPI application with an overridden dependency for session_maker
    """

    async def get_test_session():
        return session_maker

    app.dependency_overrides[get_async_session_maker] = get_test_session

    return app


@pytest_asyncio.fixture
async def async_client(test_app: FastAPI):
    """
    Creates an async client for testing endpoints
    """
    async with AsyncClient(transport=ASGITransport(test_app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def verified_user_client(
    async_client: AsyncClient, user_info: UserCreate, session_maker
) -> tuple[AsyncClient, uuid.UUID, str]:
    """Fixture creates a verified user and returns a client with a token"""
    # Create a user
    response = await async_client.post("/api/auth/register", json=user_info.model_dump())
    assert response.status_code == 201
    user_id = response.json()["id"]

    # Get the verification token
    keys = await UserService.verification_redis.keys("email_verification:*")
    for key in keys:
        value = await UserService.verification_redis.get(key)
        if value == str(user_id):
            token = key.split(":")[1]
            break

    # Verify email
    response = await async_client.post("/api/auth/verify-email", params={"token": token})
    assert response.status_code == 200

    # Log in
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


# --- Financial fixtures: shared by finance, analytics, and billing ---

BASE_TEST_URL = "http://localhost:8000"
fake = Faker()


async def create_user(session_maker) -> UserModel:
    """Creates a confirmed user directly via the service"""
    user_info = UserCreate(
        firstname=fake.first_name(),
        lastname=fake.last_name(),
        email=fake.unique.email(),
        password=fake.password(length=16),
        telegram_id=fake.random_int(min=10_000_000, max=99_999_999),
        timezone="Europe/Minsk",
    )
    return await UserService.create(user_info, base_url=BASE_TEST_URL, session_maker=session_maker)


@pytest_asyncio.fixture
async def user(user_info: UserCreate, session_maker) -> UserModel:
    """User who owns the financial data in tests"""
    return await UserService.create(user_info, base_url=BASE_TEST_URL, session_maker=session_maker)


@pytest_asyncio.fixture
async def other_user(session_maker) -> UserModel:
    """Second user for data isolation checks"""
    return await create_user(session_maker)


@pytest_asyncio.fixture
async def account(user, currencies, session_maker):
    """USD account with an initial balance"""
    return await AccountService.create_for_user(
        schema=AccountCreate(name="Cash", type=AccountType.CASH, currency_id="USD", balance=1000.0),
        user_id=user.id,
        session_maker=session_maker,
    )


@pytest_asyncio.fixture
async def second_account(user, currencies, session_maker):
    """Second user account, used in transfer tests"""
    return await AccountService.create_for_user(
        schema=AccountCreate(name="Savings", type=AccountType.SAVINGS, currency_id="USD", balance=500.0),
        user_id=user.id,
        session_maker=session_maker,
    )


@pytest_asyncio.fixture
async def expense_category(user, session_maker):
    """Expense category"""
    return await CategoryService.create_for_user(
        schema=CategoryCreate(name="Groceries", type=CategoryType.EXPENSE),
        user_id=user.id,
        session_maker=session_maker,
    )


@pytest_asyncio.fixture
async def income_category(user, session_maker):
    """Income category"""
    return await CategoryService.create_for_user(
        schema=CategoryCreate(name="Salary", type=CategoryType.INCOME),
        user_id=user.id,
        session_maker=session_maker,
    )
