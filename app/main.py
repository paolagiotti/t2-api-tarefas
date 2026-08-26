"""Ponto de entrada. Monta a aplicacao juntando as pecas do core."""
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestLoggingMiddleware, setup_logging
from app.modules.tasks.router import router as tasks_router
from app.modules.users.router import router as users_router

settings = get_settings()
setup_logging(settings.debug)


def create_app() -> FastAPI:
    """Factory: permite criar instancias isoladas nos testes."""
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Trabalho T2 - Engenharia de Software: Arquitetura e Padroes",
    )
    app.add_middleware(RequestLoggingMiddleware)
    register_exception_handlers(app)

    app.include_router(users_router)
    app.include_router(tasks_router)

    @app.get("/health", tags=["infra"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
