"""Excecoes de dominio + tradutor para HTTP.

Ideia central: a camada de servico NAO pode levantar HTTPException (isso
seria acoplar regra de negocio ao FastAPI). Ela levanta erros de dominio,
e o handler registrado aqui traduz para uma resposta HTTP padronizada.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class DomainError(Exception):
    """Erro de negocio. Nao conhece HTTP."""

    status_code = 400
    code = "domain_error"

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        if code:
            self.code = code
        super().__init__(message)


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class AuthenticationError(DomainError):
    status_code = 401
    code = "unauthenticated"


class PermissionDeniedError(DomainError):
    status_code = 403
    code = "forbidden"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError):
        logger.warning(
            "erro de dominio",
            extra={"path": request.url.path, "code": exc.code},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message}},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Dados invalidos na requisicao.",
                    "details": exc.errors(),
                }
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        # Loga o stacktrace inteiro, mas nao vaza detalhe interno pro cliente.
        logger.exception("erro nao tratado em %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error", "message": "Erro interno."}},
        )
