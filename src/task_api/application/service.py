from dataclasses import replace
from datetime import date, datetime, timedelta
from uuid import UUID, uuid4

from task_api.application.ports import Clock, Passwords, Tokens, UowFactory
from task_api.domain.model import (
    AppError,
    AuthSession,
    Comment,
    Priority,
    Role,
    Task,
    TaskStatus,
    User,
)
from task_api.domain.policy import apply_task_changes, can_view_task


def not_found() -> AppError:
    return AppError("NOT_FOUND", "Recurso não encontrado.")


def forbidden() -> AppError:
    return AppError("FORBIDDEN", "Ação não permitida.")


def unauthorized() -> AppError:
    return AppError("UNAUTHORIZED", "Autenticação inválida.")


def conflict() -> AppError:
    return AppError("CONFLICT", "Operação em conflito com o estado atual.")


def normalize_email(value: str) -> str:
    return value.strip().lower()


class TaskService:
    def __init__(
        self,
        uow_factory: UowFactory,
        passwords: Passwords,
        tokens: Tokens,
        clock: Clock,
        jwt_minutes: int = 30,
    ):
        self.uow_factory = uow_factory
        self.passwords = passwords
        self.tokens = tokens
        self.clock = clock
        self.jwt_minutes = jwt_minutes

    def register(self, name: str, email: str, password: str) -> User:
        now = self.clock()
        email = normalize_email(email)
        with self.uow_factory() as uow:
            if uow.users.by_email(email):
                raise conflict()
            user = User(
                uuid4(), name.strip(), email, self.passwords.hash(password), Role.USER, now, now
            )
            uow.users.add(user)
            uow.commit()
            return user

    def authenticate(self, token: str) -> tuple[User, UUID]:
        try:
            user_id, jti = self.tokens.decode(token)
        except ValueError as exc:
            raise unauthorized() from exc
        with self.uow_factory() as uow:
            auth_session = uow.sessions.get(jti)
            user = uow.users.get(user_id)
            if (
                auth_session is None
                or auth_session.user_id != user_id
                or auth_session.revoked_at is not None
                or auth_session.expires_at <= self.clock()
                or user is None
            ):
                raise unauthorized()
            return user, jti

    def login(self, email: str, password: str) -> tuple[str, datetime, int]:
        with self.uow_factory() as uow:
            user = uow.users.by_email(normalize_email(email))
            if user is None or user.deleted_at is not None:
                raise unauthorized()
            if not self.passwords.verify(password, user.password_hash):
                raise unauthorized()
            now = self.clock()
            expires_at = now + timedelta(minutes=self.jwt_minutes)
            jti = uuid4()
            uow.sessions.add(AuthSession(jti, user.id, now, expires_at))
            uow.commit()
            return (
                self.tokens.encode(user.id, jti, now, expires_at),
                expires_at,
                self.jwt_minutes * 60,
            )

    def logout(self, jti: UUID) -> None:
        with self.uow_factory() as uow:
            uow.sessions.revoke(jti, self.clock())
            uow.commit()

    def get_user(self, user_id: UUID) -> User:
        with self.uow_factory() as uow:
            user = uow.users.get(user_id)
            if user is None:
                raise not_found()
            return user

    def list_users(self, page: int, page_size: int) -> tuple[list[User], int]:
        with self.uow_factory() as uow:
            return uow.users.list_active(page, page_size)

    def update_user(self, actor: User, user_id: UUID, name: str, email: str) -> User:
        with self.uow_factory() as uow:
            user = uow.users.get(user_id, lock=True)
            if user is None:
                raise not_found()
            if actor.id != user_id and actor.role != Role.ADMIN:
                raise forbidden()
            normalized = normalize_email(email)
            if normalized != user.email and uow.users.by_email(normalized):
                raise conflict()
            if name.strip() == user.name and normalized == user.email:
                return user
            result = replace(user, name=name.strip(), email=normalized, updated_at=self.clock())
            uow.users.save(result)
            uow.commit()
            return result

    def delete_user(self, actor: User, user_id: UUID) -> None:
        with self.uow_factory() as uow:
            uow.lock_admins()
            user = uow.users.get(user_id, lock=True)
            if user is None:
                raise not_found()
            if actor.id != user_id and actor.role != Role.ADMIN:
                raise forbidden()
            if user.role == Role.ADMIN and uow.users.count_admins() <= 1:
                raise conflict()
            now = self.clock()
            uow.users.save(replace(user, deleted_at=now, updated_at=now))
            uow.tasks.unassign_open(user_id, now)
            uow.sessions.revoke_all(user_id, now)
            uow.commit()

    def change_role(self, actor: User, user_id: UUID, role: Role) -> User:
        if actor.role != Role.ADMIN:
            raise forbidden()
        with self.uow_factory() as uow:
            uow.lock_admins()
            user = uow.users.get(user_id, lock=True)
            if user is None:
                raise not_found()
            if user.role == Role.ADMIN and role != Role.ADMIN and uow.users.count_admins() <= 1:
                raise conflict()
            if user.role == role:
                return user
            result = replace(user, role=role, updated_at=self.clock())
            uow.users.save(result)
            uow.commit()
            return result

    def change_password(self, actor: User, user_id: UUID, current: str, new: str) -> None:
        if actor.id != user_id:
            raise forbidden()
        with self.uow_factory() as uow:
            user = uow.users.get(user_id, lock=True)
            if user is None:
                raise not_found()
            if not self.passwords.verify(current, user.password_hash):
                raise forbidden()
            now = self.clock()
            uow.users.save(replace(user, password_hash=self.passwords.hash(new), updated_at=now))
            uow.sessions.revoke_all(user_id, now)
            uow.commit()

    def create_task(
        self,
        actor: User,
        title: str,
        description: str | None,
        assigned_to: UUID | None,
        priority: Priority,
        due_at: datetime | None,
    ) -> Task:
        if actor.role == Role.GUEST:
            raise forbidden()
        with self.uow_factory() as uow:
            if assigned_to is not None and uow.users.get(assigned_to, lock=True) is None:
                raise conflict()
            now = self.clock()
            task = Task(
                uuid4(),
                title.strip(),
                description,
                TaskStatus.PENDING,
                priority,
                actor.id,
                assigned_to,
                due_at,
                None,
                now,
                now,
            )
            uow.tasks.add(task)
            uow.commit()
            return task

    def get_task(self, actor: User, task_id: UUID) -> Task:
        with self.uow_factory() as uow:
            task = uow.tasks.get(task_id)
            if task is None or not can_view_task(actor, task):
                raise not_found()
            return task

    def list_tasks(
        self,
        actor: User,
        assigned_to: UUID | None,
        status: TaskStatus | None,
        priority: Priority | None,
        due_before: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Task], int]:
        with self.uow_factory() as uow:
            return uow.tasks.list_visible(
                actor, assigned_to, status, priority, due_before, page, page_size
            )

    def update_task(self, actor: User, task_id: UUID, fields: dict) -> Task:
        with self.uow_factory() as uow:
            # Lock the assignee before the task, matching account deactivation's order.
            assignee = None
            if fields["assigned_to"] is not None:
                assignee = uow.users.get(fields["assigned_to"], lock=True)
            task = uow.tasks.get(task_id, lock=True)
            if task is None or not can_view_task(actor, task):
                raise not_found()
            if actor.role == Role.GUEST:
                raise forbidden()
            try:
                result = apply_task_changes(actor, task, fields, self.clock())
            except PermissionError as exc:
                raise forbidden() from exc
            if (
                fields["assigned_to"] is not None
                and (
                    fields["assigned_to"] != task.assigned_to or fields["status"] != TaskStatus.DONE
                )
                and assignee is None
            ):
                raise conflict()
            if result != task:
                uow.tasks.save(result)
                uow.commit()
            return result

    def delete_task(self, actor: User, task_id: UUID) -> None:
        with self.uow_factory() as uow:
            task = uow.tasks.get(task_id, lock=True)
            if task is None or not can_view_task(actor, task):
                raise not_found()
            if actor.role == Role.GUEST or (
                actor.role != Role.ADMIN and task.created_by != actor.id
            ):
                raise forbidden()
            uow.tasks.save(replace(task, deleted_at=self.clock()))
            uow.commit()

    def create_comment(self, actor: User, task_id: UUID, content: str) -> Comment:
        if actor.role == Role.GUEST:
            raise forbidden()
        with self.uow_factory() as uow:
            task = uow.tasks.get(task_id)
            if task is None or not can_view_task(actor, task):
                raise not_found()
            comment = Comment(uuid4(), task_id, actor.id, content.strip(), self.clock())
            uow.comments.add(comment)
            uow.commit()
            return comment

    def list_comments(
        self, actor: User, task_id: UUID, page: int, page_size: int
    ) -> tuple[list[Comment], int]:
        with self.uow_factory() as uow:
            task = uow.tasks.get(task_id)
            if task is None or not can_view_task(actor, task):
                raise not_found()
            return uow.comments.list_for_task(task_id, page, page_size)

    def delete_comment(self, actor: User, task_id: UUID, comment_id: UUID) -> None:
        with self.uow_factory() as uow:
            task = uow.tasks.get(task_id)
            if task is None or not can_view_task(actor, task):
                raise not_found()
            comment = uow.comments.get(comment_id)
            if comment is None or comment.task_id != task_id:
                raise not_found()
            if actor.role == Role.GUEST or (
                actor.role != Role.ADMIN and comment.author_id != actor.id
            ):
                raise forbidden()
            uow.comments.save(replace(comment, deleted_at=self.clock()))
            uow.commit()

    def bootstrap_admin(self, name: str, email: str, password: str) -> User:
        with self.uow_factory() as uow:
            uow.lock_admins()
            existing = uow.users.by_email(normalize_email(email))
            if existing:
                if existing.role == Role.ADMIN and existing.deleted_at is None:
                    return existing
                raise conflict()
            if uow.users.count_admins() != 0:
                raise conflict()
            now = self.clock()
            user = User(
                uuid4(),
                name.strip(),
                normalize_email(email),
                self.passwords.hash(password),
                Role.ADMIN,
                now,
                now,
            )
            uow.users.add(user)
            uow.commit()
            return user
