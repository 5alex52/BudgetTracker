from typing import Annotated

from fastapi import Depends
from src.users.dependencies import get_current_active_user
from src.users.schemas import User

#: Current user — shared authorization mechanism for the service
CurrentUser = Annotated[User, Depends(get_current_active_user)]
