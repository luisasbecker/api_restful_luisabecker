import pytest

from task_api.domain.model import AppError, Role
from task_api.presentation.cli import main


@pytest.fixture
def cli_environment(api, pg_settings, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", pg_settings.database_url.get_secret_value())
    monkeypatch.setenv("JWT_SECRET", pg_settings.jwt_secret.get_secret_value())
    monkeypatch.setenv("BOOTSTRAP_NAME", "CLI Admin")
    monkeypatch.setenv("BOOTSTRAP_EMAIL", "cli.admin@example.org")
    monkeypatch.setenv("BOOTSTRAP_PASSWORD", "A bootstrap test password 123")
    monkeypatch.setenv("DEMO_PASSWORD", "A demonstration test password 123")
    return api.app.state.service


def test_bootstrap_is_idempotent_and_keeps_existing_credentials(cli_environment, monkeypatch):
    service = cli_environment
    assert main(["bootstrap-admin"]) == 0
    with service.uow_factory() as uow:
        initial = uow.users.by_email("cli.admin@example.org")
    assert initial.role == Role.ADMIN
    assert service.passwords.verify("A bootstrap test password 123", initial.password_hash)
    monkeypatch.setenv("BOOTSTRAP_PASSWORD", "A different test password 456")
    assert main(["bootstrap-admin"]) == 0
    with service.uow_factory() as uow:
        repeated = uow.users.by_email(initial.email)
        assert uow.users.count_admins() == 1
    assert repeated == initial


def test_bootstrap_does_not_promote_existing_user(cli_environment, capsys):
    service = cli_environment
    original = service.register(
        "Existing", "cli.admin@example.org", "An existing test password 123"
    )
    assert main(["bootstrap-admin"]) == 1
    assert service.get_user(original.id) == original
    assert "conflito" in capsys.readouterr().err


def test_seed_creates_roles_and_preserves_existing_accounts(cli_environment, monkeypatch, capsys):
    service = cli_environment
    assert main(["bootstrap-admin"]) == 0
    assert main(["seed-demo"]) == 0
    emails = ["demo.creator@example.org", "demo.assignee@example.org", "demo.guest@example.org"]
    with service.uow_factory() as uow:
        initial = [uow.users.by_email(email) for email in emails]
    assert [user.role for user in initial] == [Role.USER, Role.USER, Role.GUEST]
    assert all(
        service.passwords.verify("A demonstration test password 123", user.password_hash)
        for user in initial
    )
    monkeypatch.setenv("DEMO_PASSWORD", "A different demo password 456")
    assert main(["seed-demo"]) == 0
    with service.uow_factory() as uow:
        assert [uow.users.by_email(email) for email in emails] == initial
    output = capsys.readouterr()
    assert output.out.count("Conta existente preservada:") == 3
    assert "A demonstration test password 123" not in output.out + output.err
    assert "A different demo password 456" not in output.out + output.err


def test_seed_propagates_non_conflict_error(cli_environment, monkeypatch, capsys):
    service = cli_environment
    assert main(["bootstrap-admin"]) == 0

    def unavailable(*_args):
        raise AppError("UNAVAILABLE", "Serviço indisponível.")

    # Exercise the CLI error boundary while retaining a real PostgreSQL admin lookup.
    monkeypatch.setattr(type(service), "register", unavailable)
    assert main(["seed-demo"]) == 1
    output = capsys.readouterr()
    assert "indisponível" in output.err
    assert "Conta existente preservada" not in output.out
