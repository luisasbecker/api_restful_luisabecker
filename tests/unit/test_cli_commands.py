from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest

from task_api.domain.model import AppError, Role
from task_api.infrastructure.settings import Settings
from task_api.presentation import cli


@pytest.fixture
def settings():
    return Settings(
        app_env="test",
        database_url="postgresql+psycopg://unit:unit@127.0.0.1/task_api",
        jwt_secret="only-for-unit-tests-very-long-secret",
        _env_file=None,
    )


def test_required_uses_environment_without_prompt(monkeypatch):
    monkeypatch.setenv("BOOTSTRAP_PASSWORD", "An environment test password")
    prompt = Mock(side_effect=AssertionError("must not prompt"))
    monkeypatch.setattr(cli.getpass, "getpass", prompt)
    assert cli.required("BOOTSTRAP_PASSWORD", hidden=True) == "An environment test password"
    prompt.assert_not_called()


def test_required_prompts_for_hidden_password(monkeypatch):
    monkeypatch.delenv("BOOTSTRAP_PASSWORD", raising=False)
    prompt = Mock(return_value="A hidden test password")
    monkeypatch.setattr(cli.getpass, "getpass", prompt)
    assert cli.required("BOOTSTRAP_PASSWORD", hidden=True) == "A hidden test password"
    prompt.assert_called_once_with("BOOTSTRAP_PASSWORD: ")


def test_bootstrap_uses_validated_input_and_never_prints_password(monkeypatch, capsys, settings):
    monkeypatch.setenv("BOOTSTRAP_NAME", "  Local Admin  ")
    monkeypatch.setenv("BOOTSTRAP_EMAIL", "admin@example.org")
    monkeypatch.setenv("BOOTSTRAP_PASSWORD", "A private test password")
    service = Mock()
    service.bootstrap_admin.return_value = SimpleNamespace(id=uuid4())
    cli.run_command("bootstrap-admin", service, settings)
    service.bootstrap_admin.assert_called_once_with(
        "Local Admin", "admin@example.org", "A private test password"
    )
    output = capsys.readouterr()
    assert "Administrador disponível:" in output.out
    assert "A private test password" not in output.out + output.err


def test_seed_is_rejected_in_production_before_accessing_database(settings):
    service = Mock()
    with pytest.raises(AppError) as caught:
        cli.run_command("seed-demo", service, settings.model_copy(update={"app_env": "production"}))
    assert caught.value.code == "FORBIDDEN"
    service.uow_factory.assert_not_called()


def test_seed_requires_admin_email(monkeypatch, settings):
    monkeypatch.delenv("BOOTSTRAP_EMAIL", raising=False)
    service = Mock()
    with pytest.raises(AppError) as caught:
        cli.run_command("seed-demo", service, settings)
    assert caught.value.code == "VALIDATION_ERROR"
    service.uow_factory.assert_not_called()


@pytest.mark.parametrize(
    "admin",
    [
        None,
        SimpleNamespace(role=Role.USER),
        SimpleNamespace(role=Role.ADMIN, deleted_at=datetime.now(UTC)),
    ],
)
def test_seed_requires_active_admin(monkeypatch, settings, admin):
    monkeypatch.setenv("BOOTSTRAP_EMAIL", " ADMIN@example.org ")
    service = Mock()
    uow = Mock()
    uow.users.by_email.return_value = admin
    service.uow_factory.return_value = SimpleContext(uow)
    with pytest.raises(AppError) as caught:
        cli.run_command("seed-demo", service, settings)
    assert caught.value.code == "FORBIDDEN"
    uow.users.by_email.assert_called_once_with("admin@example.org")
    service.register.assert_not_called()


class SimpleContext:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        return self.value

    def __exit__(self, *_args):
        return False


@pytest.mark.parametrize(
    "failure", [RuntimeError("PRIVATE-database-password"), EOFError(), KeyboardInterrupt()]
)
def test_main_sanitizes_failures_and_disposes_engine(monkeypatch, capsys, settings, failure):
    app = SimpleNamespace(state=SimpleNamespace(service=Mock(), engine=Mock()))
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "Settings", lambda: settings)
    monkeypatch.setattr(cli, "create_app", lambda _settings: app)
    monkeypatch.setattr(cli, "run_command", Mock(side_effect=failure))
    assert cli.main(["bootstrap-admin"]) == 1
    app.state.engine.dispose.assert_called_once_with()
    output = capsys.readouterr()
    assert output.err
    assert "PRIVATE-database-password" not in output.out + output.err
    assert "Traceback" not in output.err


def test_main_invalid_password_does_not_echo_value(monkeypatch, capsys, settings):
    app = SimpleNamespace(state=SimpleNamespace(service=Mock(), engine=Mock()))
    monkeypatch.setattr(cli, "load_dotenv", lambda: None)
    monkeypatch.setattr(cli, "Settings", lambda: settings)
    monkeypatch.setattr(cli, "create_app", lambda _settings: app)
    monkeypatch.setenv("BOOTSTRAP_NAME", "Local Admin")
    monkeypatch.setenv("BOOTSTRAP_EMAIL", "admin@example.org")
    monkeypatch.setenv("BOOTSTRAP_PASSWORD", "PRIVATE")
    assert cli.main(["bootstrap-admin"]) == 1
    app.state.service.bootstrap_admin.assert_not_called()
    app.state.engine.dispose.assert_called_once_with()
    output = capsys.readouterr()
    assert "inválidos" in output.err
    assert "PRIVATE" not in output.out + output.err
