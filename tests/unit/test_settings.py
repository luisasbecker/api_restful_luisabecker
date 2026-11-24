import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url

from task_api.infrastructure.settings import Settings, validate_test_database

APP_URL = "postgresql+psycopg://app:password@localhost:5432/task_api"
TEST_URL = "postgresql+psycopg://tests:password@localhost:5432/task_api_test"


def test_rejects_unsafe_test_database():
    with pytest.raises(ValueError):
        validate_test_database(
            "development", "postgresql+psycopg://x/y", "postgresql+psycopg://x/y_test"
        )
    with pytest.raises(ValueError):
        validate_test_database("test", "postgresql+psycopg://x/y", "postgresql+psycopg://x/y")
    with pytest.raises(ValueError):
        validate_test_database("test", "postgresql+psycopg://x/y", "postgresql+psycopg://x/y_prod")


@pytest.mark.parametrize("test_url", [None, ""])
def test_test_database_must_be_explicit(test_url):
    with pytest.raises(ValueError):
        validate_test_database("test", APP_URL, test_url)


@pytest.mark.parametrize(
    "test_url",
    [
        TEST_URL,
        "postgresql+psycopg://tests:p%40ss%3Aword@[::1]:5432/task_api_test",
        TEST_URL + "?sslmode=require&connect_timeout=5&application_name=pytest",
    ],
)
def test_accepts_explicit_isolated_postgres_database(test_url):
    assert validate_test_database("test", APP_URL, test_url) == test_url
    assert make_url(test_url).database == "task_api_test"


@pytest.mark.parametrize(
    "test_url",
    [
        "postgresql+psycopg://other:other@localhost:5432/task_api_test",
        "postgresql+psycopg://tests:password@127.0.0.1:5432/task_api_test",
        "postgresql+psycopg://tests:password@another-host:5433/task_api_test",
        "postgresql+psycopg://tests:password@localhost/task_api%5ftest",
        TEST_URL + "?application_name=another-connection",
    ],
)
def test_rejects_same_database_despite_credentials_host_or_url_spelling(test_url):
    with pytest.raises(ValueError):
        validate_test_database("test", TEST_URL, test_url)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://localhost/task_api_test",
        "postgresql+psycopg2://localhost/task_api_test",
        "sqlite:///task_api_test",
        "postgresql+psycopg:///task_api_test",
        "postgresql+psycopg://localhost",
        "postgresql+psycopg://localhost/",
        "postgresql+psycopg://localhost//task_api_test",
        "postgresql+psycopg://localhost/task_api%5Ftest",
        "postgresql+psycopg://localhost/%74ask_api_test",
        "postgresql+psycopg://localhost/task%2Fapi_test",
        "postgresql+psycopg://localhost/task%00api_test",
        "postgresql+psycopg://localhost/task%255Ftest",
        "postgresql+psycopg://localhost/task%ZZ_test",
        "postgresql+psycopg://localhost/task%FF_test",
        "postgresql+psycopg://localhost/dbname%3Dtask_api_test",
        "postgresql+psycopg://localhost/" + "a" * 59 + "_test",
        "postgresql+psycopg://localhost:invalid/task_api_test",
        "postgresql+psycopg://localhost:0/task_api_test",
        "postgresql+psycopg://localhost:65536/task_api_test",
        "postgresql+psycopg://[broken/task_api_test",
        "postgresql+psycopg://localhost,other/task_api_test",
        "postgresql+psycopg://%2Ftmp/task_api_test",
        "postgresql+psycopg://:password@localhost/task_api_test",
        "postgresql+psycopg://user:raw@password@localhost/task_api_test",
        "postgresql+psycopg://user%00:password@localhost/task_api_test",
        TEST_URL + "#fragment",
        TEST_URL + "#",
        " " + TEST_URL,
        TEST_URL + "\n",
        "postgresql+psycopg://local\nhost/task_api_test",
    ],
)
def test_rejects_ambiguous_or_malformed_database_urls(url):
    with pytest.raises(ValueError):
        validate_test_database("test", APP_URL, url)
    with pytest.raises(ValueError):
        validate_test_database("test", url, TEST_URL)


@pytest.mark.parametrize(
    "query",
    [
        "dbname=task_api",
        "host=another-host",
        "hostaddr=127.0.0.1",
        "port=5433",
        "user=another-user",
        "password=secret",
        "service=production",
        "options=-c%20search_path=production",
        "sslmode=require&dbname=task_api",
        "%64bname=task_api",
        "SSLMode=require",
        "sslmode=disable&sslmode=require",
        "application_name=pytest&application_name=another",
        "sslmode",
        "sslmode=unknown",
        "connect_timeout=0",
        "connect_timeout=not-a-number",
        "application_name=pytest%00",
        "application_name=%FF",
        "application_name=",
    ],
)
def test_rejects_query_overrides_and_ambiguous_options(query):
    url = TEST_URL + "?" + query
    with pytest.raises(ValueError):
        validate_test_database("test", APP_URL, url)
    with pytest.raises(ValueError):
        validate_test_database("test", url, TEST_URL)


def test_database_guard_never_includes_connection_secrets_in_errors():
    secret_url = "postgresql+psycopg://user:database-secret@localhost/task_api_test?dbname=prod"
    with pytest.raises(ValueError) as captured:
        validate_test_database("test", APP_URL, secret_url)
    assert "database-secret" not in str(captured.value)
    assert secret_url not in str(captured.value)
    assert captured.value.__suppress_context__


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


@pytest.mark.parametrize("minutes", [0, -1])
def test_settings_reject_nonpositive_token_lifetime(minutes):
    with pytest.raises(ValidationError):
        Settings(
            database_url=APP_URL,
            jwt_secret="jwt-secret-more-than-thirty-two-bytes-long",
            jwt_minutes=minutes,
            _env_file=None,
        )


def test_settings_accept_positive_token_lifetime_and_default(monkeypatch):
    monkeypatch.delenv("JWT_MINUTES", raising=False)
    defaults = {"database_url": APP_URL, "jwt_secret": "long-random-placeholder-for-settings-test"}
    assert Settings(**defaults, jwt_minutes=1, _env_file=None).jwt_minutes == 1
    assert Settings(**defaults, _env_file=None).jwt_minutes == 30


@pytest.mark.parametrize("field", ["database_url", "test_database_url"])
def test_settings_validate_both_database_url_fields(field):
    values = {"database_url": APP_URL, "jwt_secret": "long-random-placeholder-for-settings-test"}
    values[field] = "postgresql+psycopg://user:database-secret@localhost/app?host=other"
    with pytest.raises(ValidationError) as captured:
        Settings(**values, _env_file=None)
    assert "database-secret" not in str(captured.value)
