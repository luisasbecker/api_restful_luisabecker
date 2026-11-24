from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from task_api.application.service import TaskService, unauthorized
from task_api.domain.model import AppError, Comment, Priority, Role, Task, TaskStatus, User
from task_api.presentation.schemas import (
    CommentCreate,
    CommentOut,
    ErrorEnvelope,
    Login,
    PageOut,
    PasswordUpdate,
    RoleUpdate,
    TaskCreate,
    TaskOut,
    TaskUpdate,
    TokenOut,
    UserCreate,
    UserDetail,
    UserSummary,
    UserUpdate,
)

router = APIRouter()
bearer = HTTPBearer(auto_error=False, bearerFormat="JWT")


def error_responses(*codes: int) -> dict:
    descriptions = {
        401: "Autenticação inválida",
        403: "Ação proibida",
        404: "Recurso não encontrado",
        409: "Conflito",
        422: "Dados inválidos",
    }
    return {code: {"model": ErrorEnvelope, "description": descriptions[code]} for code in codes}


def get_service(request: Request) -> TaskService:
    return request.app.state.service


Service = Annotated[TaskService, Depends(get_service)]


def get_actor(
    request: Request,
    service: Service,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> tuple[User, UUID]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()
    actor, jti = service.authenticate(credentials.credentials)
    request.state.user_id = str(actor.id)
    return actor, jti


Actor = Annotated[tuple[User, UUID], Depends(get_actor)]


def strict_query(request: Request, allowed: set[str]) -> None:
    if set(request.query_params) - allowed:
        raise AppError("VALIDATION_ERROR", "Dados inválidos.")


def page(items: list, total: int, number: int, size: int) -> dict:
    return {
        "items": items,
        "total": total,
        "page": number,
        "pageSize": size,
        "totalPages": (total + size - 1) // size,
    }


def user_summary(user: User) -> UserSummary:
    return UserSummary(id=user.id, name=user.name)


def user_detail(user: User) -> UserDetail:
    return UserDetail(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def task_out(task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        priority=task.priority,
        created_by=task.created_by,
        assigned_to=task.assigned_to,
        due_at=task.due_at,
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def comment_out(comment: Comment) -> CommentOut:
    return CommentOut(
        id=comment.id,
        task_id=comment.task_id,
        author_id=comment.author_id,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.post(
    "/users",
    response_model=UserDetail,
    status_code=201,
    tags=["users"],
    responses=error_responses(409, 422),
)
def create_user(body: UserCreate, service: Service, response: Response):
    user = service.register(body.name, str(body.email), body.password)
    response.headers["Location"] = f"/users/{user.id}"
    return user_detail(user)


@router.get(
    "/users",
    response_model=PageOut[UserSummary],
    tags=["users"],
    responses=error_responses(401, 422),
)
def list_users(
    request: Request,
    service: Service,
    actor: Actor,
    page_number: Annotated[int, Query(alias="page", ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
):
    strict_query(request, {"page", "pageSize"})
    users, total = service.list_users(page_number, page_size)
    return page([user_summary(user) for user in users], total, page_number, page_size)


@router.get(
    "/users/{user_id}",
    response_model=UserDetail | UserSummary,
    tags=["users"],
    responses=error_responses(401, 404, 422),
)
def get_user(user_id: UUID, service: Service, actor: Actor):
    user = service.get_user(user_id)
    return (
        user_detail(user)
        if actor[0].id == user.id or actor[0].role == Role.ADMIN
        else user_summary(user)
    )


@router.put(
    "/users/{user_id}",
    response_model=UserDetail,
    tags=["users"],
    responses=error_responses(401, 403, 404, 409, 422),
)
def update_user(user_id: UUID, body: UserUpdate, service: Service, actor: Actor):
    return user_detail(service.update_user(actor[0], user_id, body.name, str(body.email)))


@router.delete(
    "/users/{user_id}",
    status_code=204,
    tags=["users"],
    responses=error_responses(401, 403, 404, 409, 422),
)
def delete_user(user_id: UUID, service: Service, actor: Actor):
    service.delete_user(actor[0], user_id)
    return Response(status_code=204)


@router.put(
    "/users/{user_id}/role",
    response_model=UserDetail,
    tags=["users"],
    responses=error_responses(401, 403, 404, 409, 422),
)
def update_role(user_id: UUID, body: RoleUpdate, service: Service, actor: Actor):
    return user_detail(service.change_role(actor[0], user_id, body.role))


@router.put(
    "/users/{user_id}/password",
    status_code=204,
    tags=["users"],
    responses=error_responses(401, 403, 404, 422),
)
def change_password(user_id: UUID, body: PasswordUpdate, service: Service, actor: Actor):
    service.change_password(actor[0], user_id, body.current_password, body.new_password)
    return Response(status_code=204)


@router.post(
    "/auth/login", response_model=TokenOut, tags=["auth"], responses=error_responses(401, 422)
)
def login(body: Login, service: Service):
    token, expires_at, seconds = service.login(str(body.email), body.password)
    return TokenOut(
        access_token=token, token_type="bearer", expires_in=seconds, expires_at=expires_at
    )


@router.post("/auth/logout", status_code=204, tags=["auth"], responses=error_responses(401))
def logout(service: Service, actor: Actor):
    service.logout(actor[1])
    return Response(status_code=204)


@router.post(
    "/tasks",
    response_model=TaskOut,
    status_code=201,
    tags=["tasks"],
    responses=error_responses(401, 403, 409, 422),
)
def create_task(body: TaskCreate, service: Service, actor: Actor, response: Response):
    task = service.create_task(
        actor[0], body.title, body.description, body.assigned_to, body.priority, body.due_at
    )
    response.headers["Location"] = f"/tasks/{task.id}"
    return task_out(task)


@router.get(
    "/tasks", response_model=PageOut[TaskOut], tags=["tasks"], responses=error_responses(401, 422)
)
def list_tasks(
    request: Request,
    service: Service,
    actor: Actor,
    assigned_to: Annotated[UUID | None, Query(alias="assignedTo")] = None,
    status: TaskStatus | None = None,
    priority: Priority | None = None,
    due_before: Annotated[date | None, Query(alias="dueBefore")] = None,
    page_number: Annotated[int, Query(alias="page", ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
):
    strict_query(request, {"assignedTo", "status", "priority", "dueBefore", "page", "pageSize"})
    tasks, total = service.list_tasks(
        actor[0], assigned_to, status, priority, due_before, page_number, page_size
    )
    return page([task_out(task) for task in tasks], total, page_number, page_size)


@router.get(
    "/tasks/{task_id}",
    response_model=TaskOut,
    tags=["tasks"],
    responses=error_responses(401, 404, 422),
)
def get_task(task_id: UUID, service: Service, actor: Actor):
    return task_out(service.get_task(actor[0], task_id))


@router.put(
    "/tasks/{task_id}",
    response_model=TaskOut,
    tags=["tasks"],
    responses=error_responses(401, 403, 404, 409, 422),
)
def update_task(task_id: UUID, body: TaskUpdate, service: Service, actor: Actor):
    return task_out(service.update_task(actor[0], task_id, body.model_dump()))


@router.delete(
    "/tasks/{task_id}",
    status_code=204,
    tags=["tasks"],
    responses=error_responses(401, 403, 404, 422),
)
def delete_task(task_id: UUID, service: Service, actor: Actor):
    service.delete_task(actor[0], task_id)
    return Response(status_code=204)


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentOut,
    status_code=201,
    tags=["comments"],
    responses=error_responses(401, 403, 404, 422),
)
def create_comment(
    task_id: UUID, body: CommentCreate, service: Service, actor: Actor, response: Response
):
    comment = service.create_comment(actor[0], task_id, body.content)
    response.headers["Location"] = f"/tasks/{task_id}/comments/{comment.id}"
    return comment_out(comment)


@router.get(
    "/tasks/{task_id}/comments",
    response_model=PageOut[CommentOut],
    tags=["comments"],
    responses=error_responses(401, 404, 422),
)
def list_comments(
    task_id: UUID,
    request: Request,
    service: Service,
    actor: Actor,
    page_number: Annotated[int, Query(alias="page", ge=1)] = 1,
    page_size: Annotated[int, Query(alias="pageSize", ge=1, le=100)] = 20,
):
    strict_query(request, {"page", "pageSize"})
    comments, total = service.list_comments(actor[0], task_id, page_number, page_size)
    return page([comment_out(comment) for comment in comments], total, page_number, page_size)


@router.delete(
    "/tasks/{task_id}/comments/{comment_id}",
    status_code=204,
    tags=["comments"],
    responses=error_responses(401, 403, 404, 422),
)
def delete_comment(task_id: UUID, comment_id: UUID, service: Service, actor: Actor):
    service.delete_comment(actor[0], task_id, comment_id)
    return Response(status_code=204)
