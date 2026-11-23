"""Tradução de erros para respostas HTTP.

O domínio só conhece regras de negócio; a decisão de qual status HTTP usar fica nesta camada.
Erros inesperados (500) são tratados no middleware, que também os registra no log.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.domain.exceptions import (
    AuthenticationError,
    BusinessRuleViolation,
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
)

logger = logging.getLogger(__name__)

STATUS_BY_ERROR: dict[type[DomainError], int] = {
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    BusinessRuleViolation: status.HTTP_422_UNPROCESSABLE_CONTENT,
}

# Mensagens em português para os erros de validação mais comuns do Pydantic.
VALIDATION_MESSAGES = {
    "missing": "campo obrigatório",
    "extra_forbidden": "campo não reconhecido",
    "json_invalid": "JSON inválido",
    "string_type": "deve ser um texto",
    "string_too_short": "deve ter pelo menos {min_length} caractere(s)",
    "string_too_long": "deve ter no máximo {max_length} caracteres",
    "enum": "valor inválido; valores aceitos: {expected}",
    "uuid_parsing": "identificador inválido (UUID esperado)",
    "uuid_type": "identificador inválido (UUID esperado)",
    "date_from_datetime_parsing": "data inválida; use o formato AAAA-MM-DD",
    "date_parsing": "data inválida; use o formato AAAA-MM-DD",
    "int_parsing": "deve ser um número inteiro",
    "greater_than_equal": "deve ser maior ou igual a {ge}",
    "less_than_equal": "deve ser menor ou igual a {le}",
    "value_error": "valor inválido",
}

HTTP_MESSAGES = {
    status.HTTP_404_NOT_FOUND: "Rota não encontrada",
    status.HTTP_405_METHOD_NOT_ALLOWED: "Método não permitido para esta rota",
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        status_code = next(
            (code for error, code in STATUS_BY_ERROR.items() if isinstance(exc, error)),
            status.HTTP_400_BAD_REQUEST,
        )
        logger.info("%s %s recusada (%d): %s", request.method, request.url.path, status_code, exc)
        headers = (
            {"WWW-Authenticate": "Bearer"} if status_code == status.HTTP_401_UNAUTHORIZED else None
        )
        return JSONResponse({"detail": str(exc)}, status_code=status_code, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": _field_of(error), "message": _message_of(error)} for error in exc.errors()
        ]
        return JSONResponse(
            {"detail": "Dados inválidos", "errors": errors},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = HTTP_MESSAGES.get(exc.status_code, exc.detail)
        return JSONResponse({"detail": detail}, status_code=exc.status_code, headers=exc.headers)


def _field_of(error: dict[str, Any]) -> str:
    if error["type"] == "json_invalid":
        return "body"
    return ".".join(str(part) for part in error["loc"])


def _message_of(error: dict[str, Any]) -> str:
    template = VALIDATION_MESSAGES.get(error["type"])
    if template is None:
        return error["msg"]
    context = {key: str(value) for key, value in error.get("ctx", {}).items()}
    if "expected" in context:
        context["expected"] = context["expected"].replace(" or ", " ou ")
    return template.format(**context)
