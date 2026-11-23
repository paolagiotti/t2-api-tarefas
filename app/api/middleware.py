import logging
import re
import time
from uuid import uuid4

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import RequestResponseEndpoint

from app.logging_config import request_id_var

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")

logger = logging.getLogger("app.http")


def register_request_logging(app: FastAPI) -> None:
    """Registra método, rota, status e duração de cada requisição, com um request id.

    Também é a última barreira para erros inesperados: registra o traceback uma única vez e
    devolve um 500 genérico, sem expor detalhes internos ao cliente.
    """

    @app.middleware("http")
    async def log_request(request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = _request_id_from(request)
        token = request_id_var.set(request_id)
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "%s %s -> 500 (%.1f ms)", request.method, request.url.path, _elapsed_ms(started_at)
            )
            response = JSONResponse(
                {"detail": "Erro interno do servidor"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        else:
            logger.info(
                "%s %s -> %d (%.1f ms)",
                request.method,
                request.url.path,
                response.status_code,
                _elapsed_ms(started_at),
            )
        finally:
            request_id_var.reset(token)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response


def _request_id_from(request: Request) -> str:
    received = request.headers.get(REQUEST_ID_HEADER, "")
    if _VALID_REQUEST_ID.fullmatch(received):
        return received
    return uuid4().hex[:12]


def _elapsed_ms(started_at: float) -> float:
    return (time.perf_counter() - started_at) * 1000
