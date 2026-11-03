from typing import Annotated

from fastapi import Depends
from src.users.dependencies import get_current_active_user
from src.users.schemas import User

#: Текущий пользователь — общий механизм авторизации сервиса
CurrentUser = Annotated[User, Depends(get_current_active_user)]
