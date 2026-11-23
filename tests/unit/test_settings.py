import pytest
from pydantic import ValidationError

from task_api.infrastructure.settings import Settings, validate_test_database


def test_rejects_unsafe_test_database():
    with pytest.raises(ValueError):
        validate_test_database(
            "development", "postgresql+psycopg://x/y", "postgresql+psycopg://x/y_test"
        )
    with pytest.raises(ValueError):
        validate_test_database("test", "postgresql+psycopg://x/y", "postgresql+psycopg://x/y")
    with pytest.raises(ValueError):
        validate_test_database("test", "postgresql+psycopg://x/y", "postgresql+psycopg://x/y_prod")


def test_settings_require_real_secret():
    with pytest.raises(ValueError):
        Settings(database_url="postgresql+psycopg://x/y", jwt_secret="change-me")
    with pytest.raises(ValueError):
        Settings(
            database_url="postgresql+psycopg://x/y",
            jwt_secret="replace-with-random-secret-of-at-least-32-bytes",
            _env_file=None,
        )


def test_settings_repr_hides_database_password_and_jwt_secret():
    settings = Settings(
        database_url="postgresql+psycopg://user:dbsecret@localhost/example",
        jwt_secret="jwt-secret-more-than-thirty-two-bytes-long",
        _env_file=None,
    )
    assert "dbsecret" not in repr(settings)
    assert "jwt-secret" not in repr(settings)


def test_invalid_configuration_error_does_not_echo_secret():
    with pytest.raises(ValidationError) as captured:
        Settings(
            database_url="sqlite://user:database-secret@localhost/file",
            jwt_secret="too-short-secret",
            _env_file=None,
        )
    assert "database-secret" not in str(captured.value)
    assert "too-short-secret" not in str(captured.value)
