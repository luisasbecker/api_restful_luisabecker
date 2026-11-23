import re
from datetime import UTC, datetime
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic.alias_generators import to_camel

from task_api.domain.model import Priority, Role, TaskStatus


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid", hide_input_in_errors=True
    )


class UserCreate(ApiModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class UserUpdate(ApiModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return UserCreate.trim_name(value)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return UserCreate.normalize_email(value)


class UserSummary(ApiModel):
    id: UUID
    name: str


class UserDetail(UserSummary):
    email: str
    role: Role
    created_at: datetime
    updated_at: datetime


class RoleUpdate(ApiModel):
    role: Role


class PasswordUpdate(ApiModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=128)


class Login(ApiModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        return UserCreate.normalize_email(value)


class TokenOut(ApiModel):
    access_token: str
    token_type: str
    expires_in: int
    expires_at: datetime


class TaskCreate(ApiModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    assigned_to: UUID | None = None
    priority: Priority = Priority.MEDIUM
    due_at: AwareDatetime | None = None

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("due_at", mode="before")
    @classmethod
    def require_offset(cls, value):
        if (
            value is not None
            and not isinstance(value, datetime)
            and (not isinstance(value, str) or not re.search(r"(?:Z|[+-]\d{2}:\d{2})$", value))
        ):
            raise ValueError("Data/hora deve incluir offset.")
        return value

    @field_validator("due_at")
    @classmethod
    def utc_due_at(cls, value):
        return value.astimezone(UTC) if value is not None else None


class TaskUpdate(ApiModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(max_length=5000)
    status: TaskStatus
    priority: Priority
    assigned_to: UUID | None
    due_at: AwareDatetime | None

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value):
        return TaskCreate.trim_title(value)

    @field_validator("due_at", mode="before")
    @classmethod
    def require_offset(cls, value):
        return TaskCreate.require_offset(value)

    @field_validator("due_at")
    @classmethod
    def utc_due_at(cls, value):
        return TaskCreate.utc_due_at(value)


class TaskOut(ApiModel):
    id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: Priority
    created_by: UUID
    assigned_to: UUID | None
    due_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CommentCreate(ApiModel):
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content", mode="before")
    @classmethod
    def trim_content(cls, value):
        return value.strip() if isinstance(value, str) else value


class CommentOut(ApiModel):
    id: UUID
    task_id: UUID
    author_id: UUID
    content: str
    created_at: datetime


class PageOut[T](ApiModel):
    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class ErrorDetail(ApiModel):
    field: str
    reason: str


class ErrorInfo(ApiModel):
    code: str
    message: str
    details: list[ErrorDetail]


class ErrorEnvelope(ApiModel):
    error: ErrorInfo
    request_id: UUID
