import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.middleware import register_request_logging
from app.api.routers import auth, health, tasks, users
from app.application.ports import TaskNotifier
from app.config import Settings, get_settings
from app.infrastructure.database import build_engine, build_session_factory
from app.infrastructure.notifications import (
    EmailSender,
    EmailTaskNotifier,
    LogEmailSender,
    SmtpEmailSender,
)
from app.infrastructure.security import BcryptPasswordHasher, JwtTokenService
from app.logging_config import configure_logging

logger = logging.getLogger(__name__)

DESCRIPTION = """
API REST para gestão de tarefas colaborativas: usuários criam, editam, atribuem e concluem
tarefas.

**Como autenticar:** crie um usuário em `POST /users`, faça login em `POST /auth/login` e
informe o `access_token` no botão **Authorize** (cabeçalho `Authorization: Bearer <token>`).
"""

OPENAPI_TAGS = [
    {"name": "Autenticação", "description": "Login e logout com JWT."},
    {"name": "Usuários", "description": "Cadastro e manutenção de usuários."},
    {"name": "Tarefas", "description": "Criação, atribuição e acompanhamento de tarefas."},
    {"name": "Saúde", "description": "Verificação de disponibilidade da API."},
]


def create_app(settings: Settings | None = None) -> FastAPI:
    """Monta a aplicação. É aqui que as camadas são conectadas (composition root)."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    engine = build_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info("API iniciada (ambiente: %s)", settings.environment)
        yield
        engine.dispose()
        logger.info("API encerrada")

    app = FastAPI(
        title="API de Gestão de Tarefas Colaborativas",
        version="1.0.0",
        description=DESCRIPTION,
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)
    app.state.password_hasher = BcryptPasswordHasher(rounds=settings.bcrypt_rounds)
    app.state.token_service = JwtTokenService(
        settings.jwt_secret.get_secret_value(),
        algorithm=settings.jwt_algorithm,
        expires_in=timedelta(minutes=settings.jwt_expiration_minutes),
    )
    app.state.task_notifier = build_task_notifier(settings)

    register_request_logging(app)
    register_error_handlers(app)
    for router in (auth.router, users.router, tasks.router, health.router):
        app.include_router(router)
    return app


def build_task_notifier(settings: Settings) -> TaskNotifier:
    sender: EmailSender
    if settings.notification_backend == "smtp":
        sender = SmtpEmailSender(
            settings.smtp_host,
            settings.smtp_port,
            settings.email_sender,
            username=settings.smtp_username,
            password=settings.smtp_password.get_secret_value() if settings.smtp_password else None,
            use_tls=settings.smtp_use_tls,
            timeout=settings.smtp_timeout_seconds,
        )
    else:
        sender = LogEmailSender()
    return EmailTaskNotifier(sender)
