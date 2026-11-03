import logging
from datetime import datetime
from datetime import timezone
from typing import Dict
from typing import Optional

from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security import OAuth2
from passlib.context import CryptContext
from src.users.schemas import DeviceInfo
from user_agents import parse

from ..global_utils import get_token

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(
        self,
        token_url: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": token_url, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        return get_token(request, self.auto_error)


def is_valid_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def get_device_info(user_agent: str) -> DeviceInfo:
    user_agent_parsed = parse(user_agent)
    if user_agent_parsed.is_mobile:
        device_type = "Mobile"
    elif user_agent_parsed.is_tablet:
        device_type = "Tablet"
    elif user_agent_parsed.is_pc:
        device_type = "Desktop"
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user agent"
        )

    return DeviceInfo(
        device_name=str(user_agent_parsed),
        device_type=device_type,
        last_login=datetime.now(timezone.utc),
    )
