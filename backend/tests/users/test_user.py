import logging

import pytest
from fastapi.exceptions import HTTPException
from src.users.schemas import UserCreate
from src.users.service import UserService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_create_and_get_user(user_info: UserCreate, session_maker):
    user = await UserService.create(
        user_info, base_url="http://localhost:8000", session_maker=session_maker
    )

    assert user_info.firstname == user.firstname
    assert user_info.lastname == user.lastname
    assert user_info.email == user.email
    assert user_info.telegram_id == user.telegram_id
    assert user_info.photo == user.photo
    assert user_info.git_username == user.git_username
    assert user_info.is_active == user.is_active
    assert user_info.is_verified == user.is_verified
    assert user_info.is_superuser == user.is_superuser
    assert user.created_at is not None
    assert user.updated_at is None
    assert user.last_login_at is None
    assert user.timezone == user_info.timezone
    assert user.password is not None

    retrieved_user = await UserService.get(user.id, session_maker)
    assert retrieved_user.firstname == user_info.firstname
    assert retrieved_user.firstname == user.firstname


@pytest.mark.asyncio
async def test_verify_email(user_info: UserCreate, session_maker):
    user = await UserService.create(
        user_info, base_url="http://localhost:8000", session_maker=session_maker
    )
    verification_token = await UserService._create_verification_token(user.id)
    await UserService.verify_email(verification_token, session_maker)


@pytest.mark.asyncio
async def test_update_user(user_info, session_maker):
    user = await UserService.create(
        user_info, base_url="http://localhost:8000", session_maker=session_maker
    )
    updated_info = {
        "firstname": "TEST",
        "lastname": "TEST",
        "email": "test.test@test.com",
        "telegram_id": 1234567890,
    }
    updated_user = await UserService.update(user.id, updated_info, session_maker)

    assert user.id == updated_user.id
    assert updated_info["firstname"] == updated_user.firstname
    assert updated_info["lastname"] == updated_user.lastname
    assert updated_info["email"] == updated_user.email
    assert updated_info["telegram_id"] == updated_user.telegram_id
    assert updated_user.created_at == user.created_at
    assert updated_user.photo == user.photo


@pytest.mark.asyncio
async def test_get_or_create_user(user_info, session_maker):
    new_user = await UserService.get_or_create(user_info, session_maker)
    assert new_user.firstname == user_info.firstname
    assert new_user.lastname == user_info.lastname
    assert new_user.email == user_info.email
    assert new_user.telegram_id == user_info.telegram_id
    assert new_user.photo == user_info.photo
    assert new_user.git_username == user_info.git_username

    user_info.email = "test@test.com"
    user_info.telegram_id = new_user.telegram_id - 1

    await UserService.get_or_create(user_info, session_maker)

    users_list = await UserService.get_list(session_maker=session_maker)
    assert len(users_list) == 2


@pytest.mark.asyncio
async def test_delete_user(user_info, session_maker):
    user = await UserService.create(
        user_info, base_url="http://localhost:8000", session_maker=session_maker
    )

    await UserService.delete(user.id, session_maker)

    with pytest.raises(HTTPException):
        await UserService.get(user.id, session_maker)

    with pytest.raises(HTTPException):
        await UserService.update(user.id, user_info, session_maker)

    with pytest.raises(HTTPException):
        await UserService.delete(user.id, session_maker)
