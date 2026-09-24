from datetime import UTC, date, datetime, time
from uuid import UUID

from sqlalchemy import create_engine, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from task_api.application.service import conflict
from task_api.domain.model import AuthSession, Comment, Priority, Role, Task, TaskStatus, User
from task_api.infrastructure.persistence.models import CommentRow, SessionRow, TaskRow, UserRow


def utc(value: datetime | None) -> datetime | None:
    return value.astimezone(UTC) if value is not None else None


def to_user(row: UserRow) -> User:
    return User(
        row.id,
        row.name,
        row.email,
        row.password_hash,
        Role(row.role),
        utc(row.created_at),
        utc(row.updated_at),
        utc(row.deleted_at),
    )


def to_task(row: TaskRow) -> Task:
    return Task(
        row.id,
        row.title,
        row.description,
        TaskStatus(row.status),
        Priority(row.priority),
        row.created_by,
        row.assigned_to,
        utc(row.due_at),
        utc(row.completed_at),
        utc(row.created_at),
        utc(row.updated_at),
        utc(row.deleted_at),
    )


def to_comment(row: CommentRow) -> Comment:
    return Comment(
        row.id, row.task_id, row.author_id, row.content, utc(row.created_at), utc(row.deleted_at)
    )


class SqlUsers:
    def __init__(self, session: Session):
        self.session = session

    def get(self, user_id: UUID, *, lock: bool = False) -> User | None:
        statement = select(UserRow).where(UserRow.id == user_id, UserRow.deleted_at.is_(None))
        if lock:
            statement = statement.with_for_update()
        row = self.session.scalar(statement)
        return to_user(row) if row else None

    def by_email(self, email: str) -> User | None:
        row = self.session.scalar(select(UserRow).where(UserRow.email == email))
        return to_user(row) if row else None

    def add(self, user: User) -> None:
        self.session.add(
            UserRow(
                id=user.id,
                name=user.name,
                email=user.email,
                password_hash=user.password_hash,
                role=user.role.value,
                created_at=user.created_at,
                updated_at=user.updated_at,
                deleted_at=user.deleted_at,
            )
        )

    def save(self, user: User) -> None:
        row = self.session.get(UserRow, user.id)
        row.name = user.name
        row.email = user.email
        row.password_hash = user.password_hash
        row.role = user.role.value
        row.updated_at = user.updated_at
        row.deleted_at = user.deleted_at

    def count_admins(self) -> int:
        return (
            self.session.scalar(
                select(func.count())
                .select_from(UserRow)
                .where(UserRow.role == Role.ADMIN.value, UserRow.deleted_at.is_(None))
            )
            or 0
        )

    def list_active(self, page: int, page_size: int) -> tuple[list[User], int]:
        predicate = UserRow.deleted_at.is_(None)
        total = self.session.scalar(select(func.count()).select_from(UserRow).where(predicate)) or 0
        rows = self.session.scalars(
            select(UserRow)
            .where(predicate)
            .order_by(UserRow.name, UserRow.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return [to_user(row) for row in rows], total


class SqlTasks:
    def __init__(self, session: Session):
        self.session = session

    def get(self, task_id: UUID, *, lock: bool = False) -> Task | None:
        statement = select(TaskRow).where(TaskRow.id == task_id, TaskRow.deleted_at.is_(None))
        if lock:
            statement = statement.with_for_update()
        row = self.session.scalar(statement)
        return to_task(row) if row else None

    def add(self, task: Task) -> None:
        self.session.add(
            TaskRow(
                id=task.id,
                title=task.title,
                description=task.description,
                status=task.status.value,
                priority=task.priority.value,
                created_by=task.created_by,
                assigned_to=task.assigned_to,
                due_at=task.due_at,
                completed_at=task.completed_at,
                created_at=task.created_at,
                updated_at=task.updated_at,
                deleted_at=task.deleted_at,
            )
        )

    def save(self, task: Task) -> None:
        row = self.session.get(TaskRow, task.id)
        row.title = task.title
        row.description = task.description
        row.status = task.status.value
        row.priority = task.priority.value
        row.assigned_to = task.assigned_to
        row.due_at = task.due_at
        row.completed_at = task.completed_at
        row.updated_at = task.updated_at
        row.deleted_at = task.deleted_at

    def unassign_open(self, user_id: UUID, now: datetime) -> None:
        self.session.execute(
            update(TaskRow)
            .where(
                TaskRow.assigned_to == user_id,
                TaskRow.deleted_at.is_(None),
                TaskRow.status != TaskStatus.DONE.value,
            )
            .values(assigned_to=None, updated_at=now)
        )

    def list_visible(
        self,
        actor: User,
        assigned_to: UUID | None,
        status: TaskStatus | None,
        priority: Priority | None,
        due_before: date | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Task], int]:
        predicates = [TaskRow.deleted_at.is_(None)]
        if actor.role != Role.ADMIN:
            predicates.append(or_(TaskRow.created_by == actor.id, TaskRow.assigned_to == actor.id))
        if assigned_to is not None:
            predicates.append(TaskRow.assigned_to == assigned_to)
        if status is not None:
            predicates.append(TaskRow.status == status.value)
        if priority is not None:
            predicates.append(TaskRow.priority == priority.value)
        if due_before is not None:
            predicates.append(TaskRow.due_at < datetime.combine(due_before, time.min, UTC))
        total = (
            self.session.scalar(select(func.count()).select_from(TaskRow).where(*predicates)) or 0
        )
        rows = self.session.scalars(
            select(TaskRow)
            .where(*predicates)
            .order_by(TaskRow.created_at.desc(), TaskRow.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return [to_task(row) for row in rows], total


class SqlComments:
    def __init__(self, session: Session):
        self.session = session

    def get(self, comment_id: UUID) -> Comment | None:
        row = self.session.scalar(
            select(CommentRow).where(CommentRow.id == comment_id, CommentRow.deleted_at.is_(None))
        )
        return to_comment(row) if row else None

    def add(self, comment: Comment) -> None:
        self.session.add(
            CommentRow(
                id=comment.id,
                task_id=comment.task_id,
                author_id=comment.author_id,
                content=comment.content,
                created_at=comment.created_at,
            )
        )

    def save(self, comment: Comment) -> None:
        row = self.session.get(CommentRow, comment.id)
        row.deleted_at = comment.deleted_at

    def list_for_task(self, task_id: UUID, page: int, page_size: int) -> tuple[list[Comment], int]:
        predicate = (CommentRow.task_id == task_id, CommentRow.deleted_at.is_(None))
        total = (
            self.session.scalar(select(func.count()).select_from(CommentRow).where(*predicate)) or 0
        )
        rows = self.session.scalars(
            select(CommentRow)
            .where(*predicate)
            .order_by(CommentRow.created_at, CommentRow.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return [to_comment(row) for row in rows], total


class SqlSessions:
    def __init__(self, session: Session):
        self.session = session

    def get(self, jti: UUID) -> AuthSession | None:
        row = self.session.get(SessionRow, jti)
        return (
            AuthSession(
                row.jti, row.user_id, utc(row.created_at), utc(row.expires_at), utc(row.revoked_at)
            )
            if row
            else None
        )

    def add(self, auth_session: AuthSession) -> None:
        self.session.add(
            SessionRow(
                jti=auth_session.jti,
                user_id=auth_session.user_id,
                created_at=auth_session.created_at,
                expires_at=auth_session.expires_at,
            )
        )

    def revoke(self, jti: UUID, now: datetime) -> None:
        row = self.session.get(SessionRow, jti)
        if row:
            row.revoked_at = now

    def revoke_all(self, user_id: UUID, now: datetime) -> None:
        self.session.execute(
            update(SessionRow)
            .where(SessionRow.user_id == user_id, SessionRow.revoked_at.is_(None))
            .values(revoked_at=now)
        )


class SqlUnitOfWork:
    def __init__(self, sessions: sessionmaker[Session]):
        self.session = sessions()
        self.users = SqlUsers(self.session)
        self.tasks = SqlTasks(self.session)
        self.comments = SqlComments(self.session)
        self.sessions = SqlSessions(self.session)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.session.rollback()
        self.session.close()

    def lock_admins(self) -> None:
        self.session.execute(text("SELECT pg_advisory_xact_lock(730195221)"))

    def commit(self) -> None:
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise conflict() from exc


def make_session_factory(database_url: str) -> sessionmaker[Session]:
    engine = create_engine(database_url, pool_pre_ping=True, hide_parameters=True)
    return sessionmaker(bind=engine, expire_on_commit=False)
