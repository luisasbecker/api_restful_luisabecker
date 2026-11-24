import json
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from task_api.domain.model import AppError
from task_api.infrastructure.settings import Settings
from task_api.main import create_app


def client():
    settings = Settings(
        database_url="postgresql+psycopg://local:local@127.0.0.1/unused",
        jwt_secret="test-secret-at-least-thirty-two-bytes-long",
        _env_file=None,
    )
    return TestClient(create_app(settings))


def test_health_and_openapi_do_not_require_database():
    with client() as http:
        assert http.get("/health").status_code == 200
        schema = http.get("/openapi.json").json()
        assert "/auth/login" in schema["paths"]
        assert "/tasks/{task_id}/comments" in schema["paths"]
        assert "401" in schema["paths"]["/auth/login"]["post"]["responses"]
        validation = schema["paths"]["/users"]["post"]["responses"]["422"]
        assert "ErrorEnvelope" in str(validation)
        assert "ErrorEnvelope" in str(schema["paths"]["/health"]["get"]["responses"]["500"])
        assert http.get("/redoc").status_code == 200


def test_public_registration_rejects_role_without_echoing_secret(caplog):
    secret = "sensitive-password-value"
    with client() as http:
        response = http.post(
            "/users",
            json={"name": "Ana", "email": "ana@example.org", "password": secret, "role": "admin"},
        )
        assert response.status_code == 422
        assert secret not in response.text
        assert secret not in caplog.text
        assert any(item["field"] == "role" for item in response.json()["error"]["details"])
        assert "X-Request-ID" in response.headers


def test_missing_auth_is_bearer_401():
    with client() as http:
        response = http.get("/tasks")
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
        assert response.json()["error"]["code"] == "UNAUTHORIZED"
        assert response.json()["requestId"] == response.headers["X-Request-ID"]


def test_readiness_reports_database_unavailable():
    settings = Settings(
        database_url="postgresql+psycopg://x:y@127.0.0.1:9/unavailable?connect_timeout=1",
        jwt_secret="test-secret-at-least-thirty-two-bytes-long",
        _env_file=None,
    )
    with TestClient(create_app(settings)) as http:
        response = http.get("/ready")
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "UNAVAILABLE"
        assert response.json()["requestId"] == response.headers["X-Request-ID"]


def app_logs(caplog):
    return [json.loads(record.message) for record in caplog.records if record.name == "task_api"]


@pytest.mark.parametrize(
    ("method", "path", "status", "code"),
    [
        ("GET", "/missing-sensitive-path", 404, "NOT_FOUND"),
        ("POST", "/health", 405, "METHOD_NOT_ALLOWED"),
    ],
)
def test_router_errors_use_envelope_and_request_id(caplog, method, path, status, code):
    with client() as http:
        response = http.request(method, path, headers={"X-Request-ID": "untrusted-client-id"})
    body = response.json()
    assert response.status_code == status
    assert body["error"]["code"] == code
    assert body["error"]["details"] == []
    request_id = body["requestId"]
    assert UUID(request_id).version == 4
    assert request_id == response.headers["X-Request-ID"]
    assert request_id != "untrusted-client-id"
    records = app_logs(caplog)
    assert len(records) == 1
    assert records[0]["event"] == "http_request"
    assert records[0]["status"] == status
    assert records[0]["requestId"] == request_id
    assert "missing-sensitive-path" not in json.dumps(records)
    if status == 405:
        assert "GET" in response.headers["Allow"].split(", ")


@pytest.mark.parametrize(
    ("headers", "challenge"),
    [
        (None, "Bearer"),
        ({"WWW-Authenticate": "Bearer"}, "Bearer"),
        ({"www-authenticate": 'Bearer realm="task-api"'}, 'Bearer realm="task-api"'),
    ],
)
def test_framework_http_error_keeps_auth_header_without_echoing_detail(caplog, headers, challenge):
    secret = "sensitive-exception-detail"
    http = client()

    @http.app.get("/framework-error")
    def framework_error():
        raise HTTPException(401, detail=secret, headers=headers)

    with http:
        response = http.get("/framework-error")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == challenge
    assert len(response.headers.get_list("WWW-Authenticate")) == 1
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert response.json()["requestId"] == response.headers["X-Request-ID"]
    assert secret not in response.text
    assert secret not in caplog.text


@pytest.mark.parametrize(
    "content",
    [
        '{"password":"sensitive-validation-input",',
        '{"sensitive-validation-input":"sensitive-validation-input"}',
    ],
)
def test_malformed_json_and_unknown_fields_do_not_expose_input(caplog, content):
    with client() as http:
        response = http.post(
            "/users", content=content, headers={"Content-Type": "application/json"}
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["requestId"] == response.headers["X-Request-ID"]
    assert "sensitive-validation-input" not in response.text
    assert "sensitive-validation-input" not in caplog.text


def test_unexpected_error_has_correlated_safe_logs_and_does_not_escape(caplog):
    secret = "sensitive-password-token-and-sql-parameter"
    http = client()

    @http.app.get("/failure")
    def failure():
        raise RuntimeError(secret)

    # Default raise_server_exceptions=True proves the exception cannot escape
    # to an outer ASGI error logger with its original message or traceback.
    with http:
        response = http.get("/failure", headers={"Authorization": f"Bearer {secret}"})
    assert response.status_code == 500
    body = response.json()
    assert body["error"] == {"code": "INTERNAL_ERROR", "message": "Erro interno.", "details": []}
    request_id = response.headers["X-Request-ID"]
    assert body["requestId"] == request_id
    records = app_logs(caplog)
    assert len(records) == 2
    error, request = records
    assert error["event"] == "unexpected_error"
    assert error["exceptionType"] == "RuntimeError"
    assert error["source"]["file"] == "test_http_contract.py"
    assert error["source"]["function"] == "failure"
    assert error["source"]["line"] > 0
    assert error["requestId"] == request_id
    assert request["event"] == "http_request"
    assert request["status"] == 500
    assert request["route"] == "/failure"
    assert request["requestId"] == request_id
    assert secret not in response.text
    assert secret not in caplog.text
    assert all(record.exc_info is None for record in caplog.records if record.name == "task_api")


def test_unmapped_application_error_is_internal_and_redacted(caplog):
    secret = "sensitive-unmapped-error-message"
    http = client()

    @http.app.get("/unmapped-error")
    def unmapped_error():
        raise AppError("UNMAPPED_ERROR", secret)

    with http:
        response = http.get("/unmapped-error")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert response.json()["requestId"] == response.headers["X-Request-ID"]
    assert app_logs(caplog)[0]["exceptionType"] == "AppError"
    assert secret not in response.text
    assert secret not in caplog.text
