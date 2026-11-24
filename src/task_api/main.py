import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from traceback import walk_tb
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from task_api.application.service import TaskService
from task_api.domain.model import AppError
from task_api.infrastructure.persistence.uow import (
    SqlUnitOfWork,
    database_ready,
    make_session_factory,
)
from task_api.infrastructure.security import ArgonPasswords, JwtTokens
from task_api.infrastructure.settings import Settings
from task_api.presentation.routes import router
from task_api.presentation.schemas import ErrorEnvelope

logger = logging.getLogger("task_api")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Transport-specific statuses belong at the HTTP boundary, not in the domain.
ERROR_STATUSES = {
    "UNAUTHORIZED": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "VALIDATION_ERROR": 422,
    "UNAVAILABLE": 503,
}
HTTP_ERRORS = {
    400: ("BAD_REQUEST", "Requisição inválida."),
    401: ("UNAUTHORIZED", "Autenticação inválida."),
    403: ("FORBIDDEN", "Ação proibida."),
    404: ("NOT_FOUND", "Recurso não encontrado."),
    405: ("METHOD_NOT_ALLOWED", "Método não permitido."),
    409: ("CONFLICT", "Conflito."),
    422: ("VALIDATION_ERROR", "Dados inválidos."),
    503: ("UNAVAILABLE", "Serviço indisponível."),
}


def error_body(request: Request, code: str, message: str, details: list | None = None) -> dict:
    return {
        "error": {"code": code, "message": message, "details": details or []},
        "requestId": request.state.request_id,
    }


def unexpected_response(request: Request, exc: Exception) -> JSONResponse:
    source = None
    for frame, line in walk_tb(exc.__traceback__):
        source = {
            "file": Path(frame.f_code.co_filename).name,
            "function": frame.f_code.co_name,
            "line": line,
        }
    # No exception message, traceback text, source code or frame locals: all can
    # contain passwords, SQL parameters, DSNs or bearer tokens.
    logger.error(
        json.dumps(
            {
                "time": datetime.now(UTC).isoformat(),
                "level": "ERROR",
                "event": "unexpected_error",
                "requestId": request.state.request_id,
                "exceptionType": type(exc).__name__,
                "source": source,
            }
        )
    )
    return JSONResponse(error_body(request, "INTERNAL_ERROR", "Erro interno."), status_code=500)


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
    app = FastAPI(
        title="API de Gestão de Tarefas Colaborativas",
        version="0.1.0",
        responses={
            405: {"model": ErrorEnvelope, "description": "Método não permitido"},
            500: {"model": ErrorEnvelope, "description": "Erro interno"},
        },
    )
    app.state.service = service
    app.state.engine = sessions.kw["bind"]

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        request.state.request_id = str(uuid4())
        start = perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            # Handle before ServerErrorMiddleware can re-raise and print a raw
            # traceback; keep the same request log and header for 500 responses.
            response = unexpected_response(request, exc)
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
        status = ERROR_STATUSES.get(exc.code)
        if status is None:
            return unexpected_response(request, exc)
        headers = {"WWW-Authenticate": "Bearer"} if status == 401 else {}
        return JSONResponse(
            error_body(request, exc.code, exc.message), status_code=status, headers=headers
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        fallback = (
            ("INTERNAL_ERROR", "Erro interno.")
            if exc.status_code >= 500
            else ("HTTP_ERROR", "Falha na requisição.")
        )
        code, message = HTTP_ERRORS.get(exc.status_code, fallback)
        response = JSONResponse(
            error_body(request, code, message), status_code=exc.status_code, headers=exc.headers
        )
        if exc.status_code == 401:
            response.headers.setdefault("WWW-Authenticate", "Bearer")
        return response

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

    @app.get("/health", tags=["operations"])
    def health():
        return {"status": "ok"}

    @app.get(
        "/ready",
        tags=["operations"],
        responses={503: {"model": ErrorEnvelope, "description": "Banco indisponível"}},
    )
    def ready():
        if not database_ready(app.state.engine):
            raise AppError("UNAVAILABLE", "Serviço indisponível.")
        return {"status": "ok"}

    app.include_router(router)
    return app
