from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class Role(StrEnum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Priority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class User:
    id: UUID
    name: str
    email: str
    password_hash: str
    role: Role
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


@dataclass(frozen=True)
class Task:
    id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: Priority | str
    created_by: UUID
    assigned_to: UUID | None
    due_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


@dataclass(frozen=True)
class Comment:
    id: UUID
    task_id: UUID
    author_id: UUID
    content: str
    created_at: datetime
    deleted_at: datetime | None = None


@dataclass(frozen=True)
class AuthSession:
    jti: UUID
    user_id: UUID
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None


class AppError(Exception):
    def __init__(self, status: int, code: str, message: str):
        self.status = status
        self.code = code
        self.message = message
        super().__init__(message)
