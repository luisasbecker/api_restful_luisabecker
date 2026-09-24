from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_env: str = "development"
    database_url: SecretStr
    test_database_url: SecretStr | None = None
    jwt_secret: SecretStr
    jwt_issuer: str = "task-api"
    jwt_audience: str = "task-api-client"
    jwt_minutes: int = 30

    @field_validator("database_url", "test_database_url")
    @classmethod
    def database_is_postgres(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and not value.get_secret_value().startswith("postgresql+psycopg://"):
            raise ValueError("A URL deve usar PostgreSQL com psycopg.")
        return value

    @field_validator("jwt_secret")
    @classmethod
    def valid_secret(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if len(raw.encode()) < 32 or raw == "change-me" or raw.startswith("replace-"):
            raise ValueError("JWT_SECRET deve ter ao menos 32 bytes aleatórios.")
        return value


def validate_test_database(app_env: str, database_url: str, test_database_url: str | None) -> str:
    if app_env != "test" or not test_database_url or database_url == test_database_url:
        raise ValueError("Banco de testes inseguro: ambiente/URLs inválidos.")
    name = urlsplit(test_database_url).path.lstrip("/")
    if not name.endswith("_test"):
        raise ValueError("O banco de testes deve terminar com _test.")
    return test_database_url
