from ..dao import BaseDAO
from .models import RefreshSessionModel
from .models import UserModel
from .schemas import RefreshSessionBase
from .schemas import RefreshSessionCreate
from .schemas import UserCreate
from .schemas import UserUpdate


class RefreshSessionDAO(BaseDAO[RefreshSessionModel, RefreshSessionCreate, RefreshSessionBase]):
    model = RefreshSessionModel


class UserDAO(BaseDAO[UserModel, UserCreate, UserUpdate]):
    model = UserModel
