import re
from ipaddress import IPv6Address
from urllib.parse import parse_qsl, unquote, urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _database_name(url: str) -> str:
    """Read only explicit, unambiguous PostgreSQL connection identities."""
    try:
        if (
            not url.startswith("postgresql+psycopg://")
            or "#" in url
            or any(
                character.isspace() or ord(character) < 32 or ord(character) == 127
                for character in url
            )
            or re.search(r"%(?![0-9a-fA-F]{2})", url)
        ):
            raise ValueError
        parts = urlsplit(url)
        host = parts.hostname
        if not host or parts.scheme != "postgresql+psycopg" or parts.netloc.count("@") > 1:
            raise ValueError
        authority = parts.netloc.rsplit("@", 1)[-1]
        if ":" in host:
            IPv6Address(host)
            if not re.fullmatch(r"\[[0-9a-fA-F:]+\](?::[0-9]+)?", authority):
                raise ValueError
        elif not re.fullmatch(r"[a-zA-Z0-9_.-]+(?::[0-9]+)?", authority):
            raise ValueError
        if parts.port is not None and not 1 <= parts.port <= 65535:
            raise ValueError
        if "@" in parts.netloc and not parts.username:
            raise ValueError
        for credential in (parts.username, parts.password):
            if credential is not None and any(
                ord(character) < 32 or ord(character) == 127
                for character in unquote(credential, errors="strict")
            ):
                raise ValueError

        # SQLAlchemy does not decode this path. Reject encoded/ambiguous names so
        # the identity checked here is exactly the name sent to PostgreSQL.
        name = parts.path.removeprefix("/")
        if not re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]{0,62}", name):
            raise ValueError
        options = parse_qsl(
            parts.query, keep_blank_values=True, strict_parsing=True, errors="strict"
        )
        seen = set()
        for key, value in options:
            if (
                key not in {"sslmode", "connect_timeout", "application_name"}
                or key in seen
                or not value
                or any(ord(character) < 32 or ord(character) == 127 for character in value)
            ):
                raise ValueError
            seen.add(key)
            if key == "sslmode" and value not in {
                "disable",
                "allow",
                "prefer",
                "require",
                "verify-ca",
                "verify-full",
            }:
                raise ValueError
            if key == "connect_timeout" and (
                not value.isascii() or not value.isdecimal() or int(value) < 1
            ):
                raise ValueError
        return name
    except ValueError:
        raise ValueError(
            "URL PostgreSQL inválida: use psycopg, host/banco explícitos e opções permitidas."
        ) from None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_env: str = "development"
    database_url: SecretStr
    test_database_url: SecretStr | None = None
    jwt_secret: SecretStr
    jwt_issuer: str = "task-api"
    jwt_audience: str = "task-api-client"
    jwt_minutes: int = Field(default=30, ge=1)

    @field_validator("database_url", "test_database_url")
    @classmethod
    def database_is_postgres(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None:
            _database_name(value.get_secret_value())
        return value

    @field_validator("jwt_secret")
    @classmethod
    def valid_secret(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if len(raw.encode()) < 32 or raw == "change-me" or raw.startswith("replace-"):
            raise ValueError("JWT_SECRET deve ter ao menos 32 bytes aleatórios.")
        return value


def validate_test_database(app_env: str, database_url: str, test_database_url: str | None) -> str:
    if app_env != "test" or not test_database_url:
        raise ValueError("Banco de testes inseguro: ambiente/URLs inválidos.")
    app_name = _database_name(database_url)
    test_name = _database_name(test_database_url)
    # Host aliases and different credentials can still point to the same database.
    # Require distinct names even on different servers before destructive fixtures.
    if app_name == test_name:
        raise ValueError("Banco de testes inseguro: use um nome distinto do banco da aplicação.")
    if not test_name.endswith("_test"):
        raise ValueError("O banco de testes deve terminar com _test.")
    return test_database_url
