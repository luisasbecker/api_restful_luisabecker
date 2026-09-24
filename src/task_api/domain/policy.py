from dataclasses import replace
from datetime import datetime

from task_api.domain.model import Role, Task, TaskStatus, User


def can_view_task(actor: User, task: Task) -> bool:
    return task.deleted_at is None and (
        actor.role == Role.ADMIN or task.created_by == actor.id or task.assigned_to == actor.id
    )


def apply_task_changes(actor: User, task: Task, fields: dict, now: datetime) -> Task:
    if actor.role == Role.GUEST or not can_view_task(actor, task):
        raise PermissionError
    changed = {key for key, value in fields.items() if getattr(task, key) != value}
    if actor.role != Role.ADMIN and task.created_by != actor.id and changed - {"status"}:
        raise PermissionError
    if not changed:
        return task
    completed_at = task.completed_at
    if fields["status"] == TaskStatus.DONE and task.status != TaskStatus.DONE:
        completed_at = now
    elif fields["status"] != TaskStatus.DONE:
        completed_at = None
    return replace(task, **fields, completed_at=completed_at, updated_at=now)
