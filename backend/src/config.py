from typing import List
from typing import Literal

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: Literal["LOCAL", "DEV", "TEST", "PROD"]
    LOG_LEVEL: str

    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: str

    @property
    def ASYNC_DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def SYNC_DATABASE_URL(self):
        return f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    TEST_POSTGRES_DB: str
    TEST_POSTGRES_USER: str
    TEST_POSTGRES_PASSWORD: str
    TEST_POSTGRES_HOST: str
    TEST_POSTGRES_PORT: str

    @property
    def ASYNC_TEST_DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.TEST_POSTGRES_USER}:{self.TEST_POSTGRES_PASSWORD}@{self.TEST_POSTGRES_HOST}:{self.TEST_POSTGRES_PORT}/{self.TEST_POSTGRES_DB}"

    @property
    def SYNC_TEST_DATABASE_URL(self):
        return f"postgresql+psycopg2://{self.TEST_POSTGRES_USER}:{self.TEST_POSTGRES_PASSWORD}@{self.TEST_POSTGRES_HOST}:{self.TEST_POSTGRES_PORT}/{self.TEST_POSTGRES_DB}"

    def create_ASYNC_TEST_DATABASE_URL(self, db_name: str) -> str:
        """Builds async URL for a dynamically created test database."""
        return (
            f"postgresql+asyncpg://{self.TEST_POSTGRES_USER}:{self.TEST_POSTGRES_PASSWORD}"
            f"@{self.TEST_POSTGRES_HOST}:{self.TEST_POSTGRES_PORT}/{db_name}"
        )

    def create_SYNC_TEST_DATABASE_URL(self, db_name: str) -> str:
        """Builds sync URL for a dynamically created test database."""
        return (
            f"postgresql+psycopg2://{self.TEST_POSTGRES_USER}:{self.TEST_POSTGRES_PASSWORD}"
            f"@{self.TEST_POSTGRES_HOST}:{self.TEST_POSTGRES_PORT}/{db_name}"
        )

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    CORS_ORIGINS: List[str]
    CORS_HEADERS: List[str]
    CORS_METHODS: List[str]

    #: Платёжный провайдер по умолчанию: mock | stripe | crypto
    #: Реальный эквайринг подключается сменой переменной, код биллинга при этом не меняется
    BILLING_PROVIDER: str = "mock"
    BILLING_CURRENCY: str = "USD"
    #: Ключи провайдеров: пустые значения означают «провайдер не настроен»
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    CRYPTO_API_KEY: str = ""
    CRYPTO_WEBHOOK_SECRET: str = ""
    #: Адрес фронтенда, куда провайдер вернёт пользователя после оплаты
    BILLING_RETURN_URL: str = "http://localhost:5173/settings/payments"

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    #: Вход через внешние сервисы. Пустые значения — провайдер считается
    #: ненастроенным: кнопка в интерфейсе есть, а сервер отвечает понятной ошибкой,
    #: пока ключи не выданы.
    OAUTH_GOOGLE_CLIENT_ID: str = ""
    OAUTH_GOOGLE_CLIENT_SECRET: str = ""
    OAUTH_YANDEX_CLIENT_ID: str = ""
    OAUTH_YANDEX_CLIENT_SECRET: str = ""
    OAUTH_GITHUB_CLIENT_ID: str = ""
    OAUTH_GITHUB_CLIENT_SECRET: str = ""
    #: Куда провайдер вернёт пользователя; фронтенд забирает токен оттуда
    OAUTH_RETURN_URL: str = "http://localhost:5173/"
    #: Адрес интерфейса: из писем пользователь попадает сразу на страницы приложения
    FRONTEND_URL: str = "http://localhost:5173"

    RABBIT_HOST: str = "rabbitmq"
    RABBIT_PORT: int = 5672
    RABBIT_USER: str = "user"
    RABBIT_PASSWORD: str = "password"

    model_config = SettingsConfigDict(env_file=".env", extra="allow")


settings: Settings = Settings()
