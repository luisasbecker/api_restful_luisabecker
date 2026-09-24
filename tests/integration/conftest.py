import os

import pytest
from alembic.config import Config
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import text

from alembic import command
from task_api.infrastructure.settings import Settings, validate_test_database
from task_api.main import create_app


@pytest.fixture(scope="session")
def pg_settings():
    load_dotenv()
    app_url = os.environ.get("DATABASE_URL", "")
    test_url = os.environ.get("TEST_DATABASE_URL", "")
    test_url = validate_test_database(os.environ.get("APP_ENV", ""), app_url, test_url)
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url
    try:
        command.upgrade(Config("alembic.ini"), "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
    return Settings(
        app_env="test",
        database_url=test_url,
        test_database_url=test_url,
        jwt_secret="only-for-integration-tests-very-long-secret",
        _env_file=None,
    )


@pytest.fixture
def api(pg_settings):
    app = create_app(pg_settings)
    with app.state.engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE auth_sessions, comments, tasks, users"))
    with TestClient(app) as client:
        yield client
    app.state.engine.dispose()
