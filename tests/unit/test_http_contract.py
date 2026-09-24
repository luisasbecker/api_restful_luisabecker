from fastapi.testclient import TestClient

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


def test_readiness_reports_database_unavailable():
    settings = Settings(
        database_url="postgresql+psycopg://x:y@127.0.0.1:9/unavailable?connect_timeout=1",
        jwt_secret="test-secret-at-least-thirty-two-bytes-long",
        _env_file=None,
    )
    with TestClient(create_app(settings)) as http:
        assert http.get("/ready").status_code == 503
