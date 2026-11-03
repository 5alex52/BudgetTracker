import logging
import uuid
from datetime import datetime
from datetime import timezone

import pytest
from fastapi.exceptions import HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from src.users.schemas import DeviceInfo
from src.users.schemas import UserCreate
from src.users.service import AuthService
from src.users.service import UserService
from src.users.utils import get_device_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_TEST_URL = "http://localhost:8000"


async def create_and_login_user(user_info: UserCreate, session_maker):
    password = user_info.password
    device_info = DeviceInfo(
        device_name="test", device_type="test", last_login=datetime.now(timezone.utc)
    )

    user = await UserService.create(
        user_info, base_url=BASE_TEST_URL, session_maker=session_maker
    )

    token = await AuthService.login(
        OAuth2PasswordRequestForm(username=user.email, password=password),
        device_info,
        session_maker,
    )
    return user, token


@pytest.mark.asyncio
async def test_login(user_info: UserCreate, session_maker):
    device_info = DeviceInfo(
        device_name="test", device_type="test", last_login=datetime.now(timezone.utc)
    )
    with pytest.raises(HTTPException):
        await AuthService.login(
            OAuth2PasswordRequestForm(username=user_info.email, password=1234),
            device_info,
            session_maker,
        )

    _, token = await create_and_login_user(user_info, session_maker)

    assert token.access_token is not None
    assert token.refresh_token is not None


@pytest.mark.asyncio
async def test_logout(user_info: UserCreate, session_maker):
    _, token = await create_and_login_user(user_info, session_maker)
    await AuthService.logout(token.refresh_token, session_maker)


@pytest.mark.asyncio
async def test_refresh_token(user_info: UserCreate, session_maker):
    with pytest.raises(HTTPException):
        await AuthService.refresh_token(uuid.uuid4(), session_maker)

    _, token = await create_and_login_user(user_info, session_maker)

    await AuthService.refresh_token(token.refresh_token, session_maker)


@pytest.mark.asyncio
async def test_abort_session(user_info: UserCreate, session_maker):
    user, _ = await create_and_login_user(user_info, session_maker)

    await AuthService.abort_all_sessions(user.id, session_maker)


@pytest.mark.asyncio
async def test_get_user_sessions(user_info: UserCreate, session_maker):
    user, _ = await create_and_login_user(user_info, session_maker)

    sessions = await AuthService.get_user_sessions(user.id, session_maker)
    assert len(sessions) == 1
    assert sessions[0].user_id == user.id


def test_get_device_info():
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    device_info = get_device_info(user_agent)
    assert device_info.device_name == "PC / Mac OS X 10.15.7 / Chrome 133.0.0"
    assert device_info.device_type == "Desktop"
    assert device_info.last_login is not None
