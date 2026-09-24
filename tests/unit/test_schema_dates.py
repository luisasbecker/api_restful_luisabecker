from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from task_api.presentation.schemas import TaskCreate


def test_due_at_is_normalized_to_utc():
    local = datetime(2026, 10, 1, 12, 0, tzinfo=timezone(timedelta(hours=-3)))
    parsed = TaskCreate(title="Task", dueAt=local)
    assert parsed.due_at == datetime(2026, 10, 1, 15, 0, tzinfo=UTC)
    assert parsed.due_at.tzinfo == UTC


def test_due_at_requires_iso_datetime_with_offset_in_json():
    with pytest.raises(ValidationError):
        TaskCreate(title="Task", dueAt=1790000000)
