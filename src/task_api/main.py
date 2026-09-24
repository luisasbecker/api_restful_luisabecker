import json
import logging
import sys
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from task_api.application.service import TaskService
from task_api.domain.model import AppError
from task_api.infrastructure.persistence.uow import SqlUnitOfWork, make_session_factory
from task_api.infrastructure.security import ArgonPasswords, JwtTokens
from task_api.infrastructure.settings import Settings
from task_api.presentation.routes import router

logger = logging.getLogger("task_api")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def error_body(request: Request, code: str, message: str, details: list | None = None) -> dict:
    return {
        "error": {"code": code, "message": message, "details": details or []},
        "requestId": request.state.request_id,
    }


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    sessions = make_session_factory(settings.database_url.get_secret_value())
    service = TaskService(
        lambda: SqlUnitOfWork(sessions),
        ArgonPasswords(),
        JwtTokens(
            settings.jwt_secret.get_secret_value(), settings.jwt_issuer, settings.jwt_audience
        ),
        lambda: datetime.now(UTC),
        settings.jwt_minutes,
    )
    app = FastAPI(title="API de Gestão de Tarefas Colaborativas", version="0.1.0")
    app.state.service = service
    app.state.engine = sessions.kw["bind"]

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        request.state.request_id = str(uuid4())
        start = perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        route = request.scope.get("route")
        logger.info(
            json.dumps(
                {
                    "time": datetime.now(UTC).isoformat(),
                    "level": "INFO",
                    "event": "http_request",
                    "requestId": request.state.request_id,
                    "method": request.method,
                    "route": route.path if route else "unmatched",
                    "status": response.status_code,
                    "durationMs": round((perf_counter() - start) * 1000, 2),
                    "userId": getattr(request.state, "user_id", None),
                }
            )
        )
        return response

    @app.exception_handler(AppError)
    async def domain_error(request: Request, exc: AppError):
        headers = {"WWW-Authenticate": "Bearer"} if exc.status == 401 else {}
        return JSONResponse(
            error_body(request, exc.code, exc.message), status_code=exc.status, headers=headers
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        allowed = {
            "name",
            "email",
            "password",
            "currentPassword",
            "newPassword",
            "title",
            "description",
            "status",
            "priority",
            "assignedTo",
            "dueAt",
            "content",
            "role",
            "page",
            "pageSize",
            "dueBefore",
            "user_id",
            "task_id",
            "comment_id",
        }
        details = []
        for item in exc.errors():
            field = str(item["loc"][-1])
            details.append(
                {
                    "field": field if field in allowed else "unknown",
                    "reason": "Campo obrigatório."
                    if item["type"] == "missing"
                    else "Valor inválido.",
                }
            )
        return JSONResponse(
            error_body(request, "VALIDATION_ERROR", "Dados inválidos.", details), status_code=422
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, _exc: Exception):
        logger.error(
            json.dumps(
                {
                    "time": datetime.now(UTC).isoformat(),
                    "level": "ERROR",
                    "event": "unexpected_error",
                    "requestId": request.state.request_id,
                }
            )
        )
        return JSONResponse(error_body(request, "INTERNAL_ERROR", "Erro interno."), status_code=500)

    @app.get("/health", tags=["operations"])
    def health():
        return {"status": "ok"}

    @app.get("/ready", tags=["operations"])
    def ready():
        try:
            with app.state.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return {"status": "ok"}

    app.include_router(router)
    return app
