from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient

from task_api.domain.model import AppError, Priority, Role, TaskStatus
from task_api.infrastructure.persistence.uow import SqlTasks
from task_api.main import create_app


def register(api, name, email):
    response = api.post(
        "/users", json={"name": name, "email": email, "password": "A safe test password 123"}
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def token(api, email):
    response = api.post(
        "/auth/login", json={"email": email, "password": "A safe test password 123"}
    )
    assert response.status_code == 200, response.text
    return response.json()["accessToken"]


def headers(jwt):
    return {"Authorization": f"Bearer {jwt}"}


def task_body(title="Task", assigned_to=None, status="pending"):
    return {
        "title": title,
        "description": None,
        "status": status,
        "priority": "medium",
        "assignedTo": assigned_to,
        "dueAt": None,
    }


def test_registration_profile_and_persistent_logout(api, pg_settings):
    ana = register(api, "Ana", " Ana@Example.org ")
    register(api, "Bia", "bia@example.org")
    ana_token = token(api, "ana@example.org")
    second_ana_token = token(api, "ana@example.org")
    bia_token = token(api, "bia@example.org")
    assert set(api.get(f"/users/{ana}", headers=headers(bia_token)).json()) == {"id", "name"}
    assert api.get(f"/users/{ana}", headers=headers(ana_token)).json()["email"] == "ana@example.org"
    assert api.post("/auth/logout", headers=headers(ana_token)).status_code == 204
    assert api.get("/users", headers=headers(ana_token)).status_code == 401
    assert api.get("/users", headers=headers(second_ana_token)).status_code == 200
    with TestClient(create_app(pg_settings)) as restarted:
        assert restarted.get("/users", headers=headers(ana_token)).status_code == 401
        assert restarted.get("/users", headers=headers(bia_token)).status_code == 200


def test_assignee_put_is_atomic_and_visibility_filters_are_scoped(api):
    owner = register(api, "Owner", "owner@example.org")
    assignee = register(api, "Assignee", "assignee@example.org")
    outsider = register(api, "Outsider", "outsider@example.org")
    owner_token = token(api, "owner@example.org")
    assignee_token = token(api, "assignee@example.org")
    outsider_token = token(api, "outsider@example.org")
    created = api.post(
        "/tasks", json={"title": "Task", "assignedTo": assignee}, headers=headers(owner_token)
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]
    assert api.get(f"/tasks/{task_id}", headers=headers(outsider_token)).status_code == 404
    assert (
        api.get("/tasks", params={"assignedTo": assignee}, headers=headers(outsider_token)).json()[
            "total"
        ]
        == 0
    )
    denied = api.put(
        f"/tasks/{task_id}",
        json=task_body("Forbidden", assignee, "done"),
        headers=headers(assignee_token),
    )
    assert denied.status_code == 403
    assert api.get(f"/tasks/{task_id}", headers=headers(owner_token)).json()["status"] == "pending"
    done = api.put(
        f"/tasks/{task_id}",
        json=task_body(assigned_to=assignee, status="done"),
        headers=headers(assignee_token),
    )
    assert done.status_code == 200, done.text
    repeated = api.put(
        f"/tasks/{task_id}",
        json=task_body(assigned_to=assignee, status="done"),
        headers=headers(assignee_token),
    )
    assert repeated.json()["completedAt"] == done.json()["completedAt"]
    assert repeated.json()["updatedAt"] == done.json()["updatedAt"]
    assert owner != outsider


def test_comment_parent_authorization_and_guest(api):
    owner_id = register(api, "Owner", "owner@example.org")
    guest_id = register(api, "Guest", "guest@example.org")
    other_id = register(api, "Other", "other@example.org")
    service = api.app.state.service
    admin = service.bootstrap_admin("Admin", "admin@example.org", "A safe test password 123")
    guest = service.get_user(UUID(guest_id))
    service.change_role(admin, guest.id, Role.GUEST)
    owner_token = token(api, "owner@example.org")
    guest_token = token(api, "guest@example.org")
    other_token = token(api, "other@example.org")
    first = api.post(
        "/tasks", json={"title": "One", "assignedTo": guest_id}, headers=headers(owner_token)
    ).json()["id"]
    second = api.post("/tasks", json={"title": "Two"}, headers=headers(owner_token)).json()["id"]
    comment = api.post(
        f"/tasks/{first}/comments", json={"content": "hello"}, headers=headers(owner_token)
    )
    assert comment.status_code == 201
    comment_id = comment.json()["id"]
    assert api.get(f"/tasks/{first}/comments", headers=headers(guest_token)).status_code == 200
    assert (
        api.post(
            f"/tasks/{first}/comments", json={"content": "no"}, headers=headers(guest_token)
        ).status_code
        == 403
    )
    assert (
        api.delete(
            f"/tasks/{second}/comments/{comment_id}", headers=headers(owner_token)
        ).status_code
        == 404
    )
    assert api.get(f"/tasks/{first}/comments", headers=headers(other_token)).status_code == 404
    assert owner_id != other_id


def test_concurrent_admin_demotions_keep_one_active(api):
    service = api.app.state.service
    first = service.bootstrap_admin("First", "first@example.org", "A safe test password 123")
    second_id = register(api, "Second", "second@example.org")
    second = service.change_role(first, UUID(second_id), Role.ADMIN)
    barrier = Barrier(2)

    def demote(actor):
        barrier.wait()
        try:
            service.change_role(actor, actor.id, Role.USER)
            return "ok"
        except AppError as exc:
            return exc.status

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(demote, [first, second]))
    assert sorted(outcomes, key=str) == sorted(["ok", 409], key=str)
    with service.uow_factory() as uow:
        assert uow.users.count_admins() == 1


def test_concurrent_assignment_and_deactivation_leave_no_open_assignment(api):
    service = api.app.state.service
    owner_id = register(api, "Owner", "owner@example.org")
    assignee_id = register(api, "Assignee", "assignee@example.org")
    owner = service.get_user(UUID(owner_id))
    assignee = service.get_user(UUID(assignee_id))
    task = service.create_task(owner, "Task", None, None, Priority.MEDIUM, None)
    barrier = Barrier(2)

    def assign():
        barrier.wait()
        try:
            service.update_task(
                owner,
                task.id,
                {
                    "title": "Task",
                    "description": None,
                    "status": TaskStatus.PENDING,
                    "priority": task.priority,
                    "assigned_to": assignee.id,
                    "due_at": None,
                },
            )
        except AppError as exc:
            assert exc.status == 409

    def deactivate():
        barrier.wait()
        service.delete_user(assignee, assignee.id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(assign), pool.submit(deactivate)]
        for future in futures:
            future.result()
    assert service.get_task(owner, task.id).assigned_to is None


def test_password_role_and_soft_delete_preserve_history(api):
    owner_id = register(api, "Owner", "owner@example.org")
    assigned_id = register(api, "Assigned", "assigned@example.org")
    service = api.app.state.service
    admin = service.bootstrap_admin("Admin", "admin@example.org", "A safe test password 123")
    owner_token = token(api, "owner@example.org")
    assigned_token = token(api, "assigned@example.org")
    open_id = api.post(
        "/tasks", json={"title": "Open", "assignedTo": assigned_id}, headers=headers(owner_token)
    ).json()["id"]
    done_id = api.post(
        "/tasks", json={"title": "Done", "assignedTo": assigned_id}, headers=headers(owner_token)
    ).json()["id"]
    done = api.put(
        f"/tasks/{done_id}",
        json=task_body("Done", assigned_id, "done"),
        headers=headers(owner_token),
    )
    assert done.status_code == 200
    assert (
        api.put(
            f"/users/{assigned_id}/password",
            json={
                "currentPassword": "A safe test password 123",
                "newPassword": "A different test password 123",
            },
            headers=headers(assigned_token),
        ).status_code
        == 204
    )
    assert api.get(f"/tasks/{open_id}", headers=headers(assigned_token)).status_code == 401
    new_token = api.post(
        "/auth/login",
        json={"email": "assigned@example.org", "password": "A different test password 123"},
    ).json()["accessToken"]
    assert api.get(f"/tasks/{open_id}", headers=headers(new_token)).status_code == 200
    assert api.delete(f"/users/{assigned_id}", headers=headers(new_token)).status_code == 204
    assert api.get(f"/tasks/{open_id}", headers=headers(new_token)).status_code == 401
    assert api.get(f"/tasks/{open_id}", headers=headers(owner_token)).json()["assignedTo"] is None
    assert (
        api.get(f"/tasks/{done_id}", headers=headers(owner_token)).json()["assignedTo"]
        == assigned_id
    )
    denied = api.put(
        f"/tasks/{done_id}",
        json=task_body("Done", assigned_id, "pending"),
        headers=headers(owner_token),
    )
    assert denied.status_code == 409
    assert (
        api.put(
            f"/tasks/{done_id}",
            json=task_body("Done", None, "pending"),
            headers=headers(owner_token),
        ).status_code
        == 200
    )
    assert api.get(f"/tasks/{done_id}", headers=headers(owner_token)).json()["completedAt"] is None
    assert (
        api.post(
            "/users",
            json={
                "name": "Duplicate",
                "email": "assigned@example.org",
                "password": "A safe test password 123",
            },
        ).status_code
        == 409
    )
    assert service.get_user(UUID(owner_id)).id == UUID(owner_id)
    assert admin.role == Role.ADMIN


def test_filters_due_before_are_exclusive_and_scoped(api):
    register(api, "Owner", "owner@example.org")
    register(api, "Other", "other@example.org")
    owner_token = token(api, "owner@example.org")
    other_token = token(api, "other@example.org")
    for title, due_at in (
        ("Early", "2026-09-30T23:59:59Z"),
        ("Boundary", "2026-10-01T00:00:00Z"),
        ("OffsetBoundary", "2026-09-30T21:00:00-03:00"),
        ("Null", None),
    ):
        response = api.post(
            "/tasks", json={"title": title, "dueAt": due_at}, headers=headers(owner_token)
        )
        assert response.status_code == 201, response.text
    api.post(
        "/tasks",
        json={"title": "Hidden", "dueAt": "2026-09-30T00:00:00Z"},
        headers=headers(other_token),
    )
    early = api.get(
        "/tasks",
        params={"dueBefore": "2026-10-01", "status": "pending", "priority": "medium"},
        headers=headers(owner_token),
    )
    assert early.status_code == 200
    assert early.json()["total"] == 1
    assert early.json()["items"][0]["title"] == "Early"
    empty_page = api.get(
        "/tasks",
        params={"page": 2, "pageSize": 1, "dueBefore": "2026-10-01"},
        headers=headers(owner_token),
    )
    assert empty_page.json()["items"] == []
    assert empty_page.json()["total"] == 1
    assert (
        api.get("/tasks", params={"unknown": "x"}, headers=headers(owner_token)).status_code == 422
    )


def test_jwt_requires_session_and_role_is_current(api):
    user_id = register(api, "User", "user@example.org")
    service = api.app.state.service
    admin = service.bootstrap_admin("Admin", "admin@example.org", "A safe test password 123")
    user_token = token(api, "user@example.org")
    now = datetime.now(UTC)
    unknown_session = jwt.encode(
        {
            "sub": user_id,
            "jti": "1496b64a-b07b-495a-b8ee-639112c44775",
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=30),
            "iss": "task-api",
            "aud": "task-api-client",
        },
        service.tokens.secret,
        algorithm="HS256",
    )
    assert api.get("/users", headers=headers(unknown_session)).status_code == 401
    service.change_role(admin, UUID(user_id), Role.GUEST)
    assert api.get("/users", headers=headers(user_token)).status_code == 200
    assert (
        api.post("/tasks", json={"title": "Denied"}, headers=headers(user_token)).status_code == 403
    )
    wrong = api.post(
        "/auth/login", json={"email": "absent@example.org", "password": "wrong password"}
    )
    assert wrong.status_code == 401
    assert (
        wrong.json()["error"]["message"]
        == api.post(
            "/auth/login", json={"email": "user@example.org", "password": "wrong password"}
        ).json()["error"]["message"]
    )


def test_failed_user_deletion_rolls_back_every_change(api, monkeypatch):
    owner_id = register(api, "Owner", "owner@example.org")
    assigned_id = register(api, "Assigned", "assigned@example.org")
    owner_token = token(api, "owner@example.org")
    assigned_token = token(api, "assigned@example.org")
    task_id = api.post(
        "/tasks", json={"title": "Task", "assignedTo": assigned_id}, headers=headers(owner_token)
    ).json()["id"]

    def broken_unassign(self, user_id, now):
        raise RuntimeError("injected failure")

    monkeypatch.setattr(SqlTasks, "unassign_open", broken_unassign)
    service = api.app.state.service
    with pytest.raises(RuntimeError):
        service.delete_user(service.get_user(UUID(assigned_id)), UUID(assigned_id))
    assert api.get(f"/tasks/{task_id}", headers=headers(assigned_token)).status_code == 200
    assert (
        api.get(f"/tasks/{task_id}", headers=headers(owner_token)).json()["assignedTo"]
        == assigned_id
    )
    assert service.get_user(UUID(owner_id)).id == UUID(owner_id)


def test_duplicate_registration_race_returns_one_conflict(api):
    barrier = Barrier(2)
    service = api.app.state.service

    def create():
        barrier.wait()
        try:
            service.register("Racer", "racer@example.org", "A safe test password 123")
            return 201
        except AppError as exc:
            return exc.status

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _index: create(), range(2)))
    assert sorted(outcomes) == [201, 409]


def test_comment_author_only_and_deleted_parent_is_hidden(api):
    owner_id = register(api, "Owner", "owner@example.org")
    assignee_id = register(api, "Assignee", "assignee@example.org")
    owner_token = token(api, "owner@example.org")
    assignee_token = token(api, "assignee@example.org")
    task_id = api.post(
        "/tasks", json={"title": "Task", "assignedTo": assignee_id}, headers=headers(owner_token)
    ).json()["id"]
    comment_id = api.post(
        f"/tasks/{task_id}/comments", json={"content": "Comment"}, headers=headers(assignee_token)
    ).json()["id"]
    assert (
        api.delete(
            f"/tasks/{task_id}/comments/{comment_id}", headers=headers(owner_token)
        ).status_code
        == 403
    )
    assert (
        api.delete(
            f"/tasks/{task_id}/comments/{comment_id}", headers=headers(assignee_token)
        ).status_code
        == 204
    )
    assert api.get(f"/tasks/{task_id}/comments", headers=headers(owner_token)).json()["total"] == 0
    assert api.delete(f"/tasks/{task_id}", headers=headers(owner_token)).status_code == 204
    assert api.get(f"/tasks/{task_id}", headers=headers(owner_token)).status_code == 404
    assert api.get(f"/tasks/{task_id}/comments", headers=headers(owner_token)).status_code == 404
    assert owner_id != assignee_id


def test_guest_historical_creator_is_read_only_and_last_admin_is_protected(api):
    user_id = register(api, "Creator", "creator@example.org")
    user_token = token(api, "creator@example.org")
    task_id = api.post("/tasks", json={"title": "Owned"}, headers=headers(user_token)).json()["id"]
    service = api.app.state.service
    admin = service.bootstrap_admin("Admin", "admin@example.org", "A safe test password 123")
    admin_token = token(api, "admin@example.org")
    assert api.delete(f"/users/{admin.id}", headers=headers(admin_token)).status_code == 409
    assert (
        api.put(
            f"/users/{admin.id}/role", json={"role": "user"}, headers=headers(admin_token)
        ).status_code
        == 409
    )
    assert (
        api.put(
            f"/users/{user_id}/role", json={"role": "guest"}, headers=headers(admin_token)
        ).status_code
        == 200
    )
    assert api.get(f"/tasks/{task_id}", headers=headers(user_token)).status_code == 200
    assert (
        api.put(
            f"/tasks/{task_id}", json=task_body("Owned"), headers=headers(user_token)
        ).status_code
        == 403
    )
    assert api.delete(f"/tasks/{task_id}", headers=headers(user_token)).status_code == 403
    assert (
        api.put(
            f"/users/{user_id}",
            json={"name": "Renamed", "email": "creator@example.org"},
            headers=headers(user_token),
        ).status_code
        == 200
    )


def test_validation_rejects_naive_time_unknown_query_and_server_fields(api):
    register(api, "User", "user@example.org")
    user_token = token(api, "user@example.org")
    assert (
        api.post(
            "/tasks",
            json={"title": "Task", "dueAt": "2026-10-01T12:00:00"},
            headers=headers(user_token),
        ).status_code
        == 422
    )
    assert (
        api.post(
            "/tasks", json={"title": "Task", "createdBy": "forged"}, headers=headers(user_token)
        ).status_code
        == 422
    )
    task_id = api.post("/tasks", json={"title": "Task"}, headers=headers(user_token)).json()["id"]
    assert (
        api.put(
            f"/tasks/{task_id}",
            json={**task_body(), "completedAt": "forged"},
            headers=headers(user_token),
        ).status_code
        == 422
    )
    user_id = api.get("/users", headers=headers(user_token)).json()["items"][0]["id"]
    assert (
        api.put(
            f"/users/{user_id}",
            json={"name": "User", "email": "user@example.org", "role": "admin"},
            headers=headers(user_token),
        ).status_code
        == 422
    )
    assert (
        api.post(
            f"/tasks/{task_id}/comments", json={"content": "   "}, headers=headers(user_token)
        ).status_code
        == 422
    )
    assert (
        api.get("/tasks", params={"pageSize": 101}, headers=headers(user_token)).status_code == 422
    )
    assert (
        api.get("/tasks", params={"dueBefore": "bad-date"}, headers=headers(user_token)).status_code
        == 422
    )
    assert (
        api.get("/tasks", params={"status": "wrong"}, headers=headers(user_token)).status_code
        == 422
    )
    assert api.get("/tasks/not-a-uuid", headers=headers(user_token)).status_code == 422
    directory = api.get("/users", headers=headers(user_token)).json()
    assert set(directory["items"][0]) == {"id", "name"}


def test_profile_admin_and_reassignment_access(api):
    first_id = register(api, "First", "first@example.org")
    second_id = register(api, "Second", "second@example.org")
    third_id = register(api, "Third", "third@example.org")
    first_token = token(api, "first@example.org")
    second_token = token(api, "second@example.org")
    third_token = token(api, "third@example.org")
    service = api.app.state.service
    admin = service.bootstrap_admin("Admin", "admin@example.org", "A safe test password 123")
    admin_token = token(api, "admin@example.org")
    assert (
        api.get(f"/users/{first_id}", headers=headers(admin_token)).json()["email"]
        == "first@example.org"
    )
    assert (
        api.put(
            f"/users/{first_id}",
            json={"name": "Changed", "email": "first@example.org"},
            headers=headers(second_token),
        ).status_code
        == 403
    )
    assert (
        api.put(
            f"/users/{first_id}", json={"name": "Changed"}, headers=headers(first_token)
        ).status_code
        == 422
    )
    assert (
        api.put(
            f"/users/{second_id}/role", json={"role": "admin"}, headers=headers(first_token)
        ).status_code
        == 403
    )
    task_id = api.post(
        "/tasks", json={"title": "Task", "assignedTo": second_id}, headers=headers(first_token)
    ).json()["id"]
    assert api.get(f"/tasks/{task_id}", headers=headers(second_token)).status_code == 200
    response = api.put(
        f"/tasks/{task_id}", json=task_body("Task", third_id), headers=headers(first_token)
    )
    assert response.status_code == 200
    assert api.get(f"/tasks/{task_id}", headers=headers(second_token)).status_code == 404
    assert api.get(f"/tasks/{task_id}/comments", headers=headers(second_token)).status_code == 404
    assert api.get(f"/tasks/{task_id}", headers=headers(third_token)).status_code == 200
    assert api.get(f"/tasks/{task_id}", headers=headers(admin_token)).status_code == 200
    assert admin.role == Role.ADMIN
