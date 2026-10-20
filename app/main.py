import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.middleware import register_request_logging
from app.api.routers import health
from app.config import Settings, get_settings
from app.logging_config import configure_logging

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Monta a aplicação. É o ponto onde as camadas são conectadas (composition root)."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("API iniciada (ambiente: %s)", settings.environment)
        yield
        logger.info("API encerrada")

    app = FastAPI(
        title="API de Gestão de Tarefas Colaborativas",
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.settings = settings

    register_request_logging(app)
    app.include_router(health.router)
    return app
