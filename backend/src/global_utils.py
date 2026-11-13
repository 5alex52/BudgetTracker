import jwt
from typing import Optional

from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from fastapi.security.utils import get_authorization_scheme_param

from .config import settings
from .exceptions import InvalidTokenException


def get_user_id(request: Request):
    return verify_token(request)


def verify_token(request: Optional[Request] = None, token: Optional[str] = None) -> Optional[str]:
    if token is None:
        if request is None:
            raise InvalidTokenException
        token = get_token(request)
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise InvalidTokenException
    except Exception:
        raise InvalidTokenException
    return str(user_id)


def get_token(request: Request, auto_error=True):
    authorization: str = request.cookies.get("access_token")

    scheme, param = get_authorization_scheme_param(authorization)
    if not authorization or scheme.lower() != "bearer":
        if auto_error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            return None
    return param


_TIME_UNITS = (
    ("day", 24 * 60 * 60),
    ("hour", 60 * 60),
    ("minute", 60),
    ("second", 1),
)

_COMPACT_SUFFIXES = {"day": "d", "hour": "h", "minute": "m", "second": "s"}


def get_human_readable_time(seconds: float, compact: bool = False, use_days: bool = True) -> str:
    """Formats a duration in seconds into a human readable string.

    >>> get_human_readable_time(24 * 60 * 60, compact=True, use_days=False)
    '24h'
    >>> get_human_readable_time(90)
    '1 minute'
    """
    if seconds < 0:
        raise ValueError("seconds must be a positive number")

    units = _TIME_UNITS if use_days else _TIME_UNITS[1:]
    for name, unit_size in units:
        if seconds >= unit_size:
            value = int(seconds // unit_size)
            if compact:
                return f"{value}{_COMPACT_SUFFIXES[name]}"
            return f"{value} {name}{'s' if value != 1 else ''}"

    return "0s" if compact else "0 seconds"


def get_client_ip(request: Request):
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.client.host
    return ip
