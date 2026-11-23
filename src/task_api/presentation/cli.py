import argparse
import getpass
import os

from dotenv import load_dotenv

from task_api.domain.model import AppError, Role
from task_api.infrastructure.settings import Settings
from task_api.main import create_app
from task_api.presentation.schemas import UserCreate


def required(name: str, *, hidden: bool = False) -> str:
    value = os.environ.get(name)
    if value:
        return value
    return getpass.getpass(f"{name}: ") if hidden else input(f"{name}: ")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Administração explícita da API")
    parser.add_argument("command", choices=["bootstrap-admin", "seed-demo"])
    args = parser.parse_args()
    settings = Settings()
    service = create_app(settings).state.service
    if args.command == "bootstrap-admin":
        data = UserCreate(
            name=required("BOOTSTRAP_NAME"),
            email=required("BOOTSTRAP_EMAIL"),
            password=required("BOOTSTRAP_PASSWORD", hidden=True),
        )
        user = service.bootstrap_admin(data.name, str(data.email), data.password)
        print(f"Administrador disponível: {user.id}")
        return
    if settings.app_env not in {"development", "test"}:
        raise SystemExit("Seed permitido somente em development/test.")
    admin_email = os.environ.get("BOOTSTRAP_EMAIL")
    if not admin_email:
        raise SystemExit("BOOTSTRAP_EMAIL é necessário para o seed.")
    with service.uow_factory() as uow:
        admin = uow.users.by_email(admin_email.strip().lower())
    if admin is None or admin.role != Role.ADMIN or admin.deleted_at is not None:
        raise SystemExit("Administrador de demonstração inválido.")
    password = required("DEMO_PASSWORD", hidden=True)
    data = [
        UserCreate(name=name, email=email, password=password)
        for name, email in (
            ("Demo Criador", "demo.creator@example.org"),
            ("Demo Responsável", "demo.assignee@example.org"),
            ("Demo Convidado", "demo.guest@example.org"),
        )
    ]
    for entry in data:
        try:
            user = service.register(entry.name, str(entry.email), entry.password)
        except AppError as exc:
            if exc.status != 409:
                raise
            print(f"Conta existente preservada: {entry.email}")
            continue
        if entry.email == "demo.guest@example.org":
            service.change_role(admin, user.id, Role.GUEST)
        print(f"Conta criada: {entry.email} ({user.id})")


if __name__ == "__main__":
    main()
