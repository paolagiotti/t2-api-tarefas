"""Tradução das exceções de domínio para respostas HTTP.

O domínio só conhece regras de negócio; a decisão de qual status HTTP usar fica nesta camada.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        status_code = next(
            (code for error, code in STATUS_BY_ERROR.items() if isinstance(exc, error)),
            status.HTTP_400_BAD_REQUEST,
        )
        logger.info("%s %s recusada (%d): %s", request.method, request.url.path, status_code, exc)
        headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
        return JSONResponse({"detail": str(exc)}, status_code=status_code, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"field": ".".join(str(part) for part in error["loc"]), "message": error["msg"]}
            for error in exc.errors()
        ]
        return JSONResponse(
            {"detail": "Dados inválidos", "errors": errors},
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, __: Exception) -> JSONResponse:
        # O erro completo já foi registrado no log pelo middleware; o cliente recebe só isto.
        return JSONResponse(
            {"detail": "Erro interno do servidor"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
