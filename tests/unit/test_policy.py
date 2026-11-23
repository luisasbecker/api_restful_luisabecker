from datetime import UTC, datetime
from uuid import uuid4

import pytest

from task_api.domain.model import Role, Task, TaskStatus, User
from task_api.domain.policy import apply_task_changes, can_view_task


def sample_user(role=Role.USER):
    now = datetime.now(UTC)
    return User(uuid4(), "Ana", "ana@example.test", "hash", role, now, now)


def sample_task(owner, assignee):
    now = datetime.now(UTC)
    return Task(
        uuid4(),
        "Title",
        None,
        TaskStatus.PENDING,
        "medium",
        owner.id,
        assignee.id,
        None,
        None,
        now,
        now,
    )


def test_visibility_is_resource_specific():
    owner, assignee, outsider = sample_user(), sample_user(), sample_user()
    task = sample_task(owner, assignee)
    assert can_view_task(owner, task)
    assert can_view_task(assignee, task)
    assert not can_view_task(outsider, task)
    assert can_view_task(sample_user(Role.ADMIN), task)


def test_assignee_cannot_mix_status_and_title_change():
    owner, assignee = sample_user(), sample_user()
    task = sample_task(owner, assignee)
    fields = dict(
        title="Changed",
        description=None,
        status=TaskStatus.DONE,
        priority="medium",
        assigned_to=assignee.id,
        due_at=None,
    )
    with pytest.raises(PermissionError):
        apply_task_changes(assignee, task, fields, datetime.now(UTC))
    assert task.status == TaskStatus.PENDING
    assert task.title == "Title"


def test_repeating_done_preserves_timestamps():
    owner = sample_user()
    task = sample_task(owner, owner)
    fields = dict(
        title="Title",
        description=None,
        status=TaskStatus.DONE,
        priority="medium",
        assigned_to=owner.id,
        due_at=None,
    )
    first = apply_task_changes(owner, task, fields, datetime.now(UTC))
    second = apply_task_changes(owner, first, fields, datetime.now(UTC))
    assert second.completed_at == first.completed_at
    assert second.updated_at == first.updated_at
