import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.config import Settings
from app.infrastructure import models  # noqa: F401  (registra as tabelas no metadata)
from app.infrastructure.database import Base, build_engine, build_session_factory
from app.main import create_app

# Por padrão os testes usam SQLite em memória. Defina TEST_DATABASE_URL para rodá-los
# contra um PostgreSQL de verdade (é o que o pipeline de CI faz).
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite://")
PASSWORD = "senha-segura-123"


@dataclass(frozen=True)
class ApiUser:
    id: str
    email: str
    headers: dict[str, str]


@pytest.fixture
def settings() -> Settings:
    # _env_file=None garante que o .env de quem roda os testes não interfira.
    return Settings(
        _env_file=None,
        environment="test",
        log_level="WARNING",
        database_url=TEST_DATABASE_URL,
        jwt_secret="segredo-de-teste-com-pelo-menos-32-caracteres",
        bcrypt_rounds=4,
    )


@pytest.fixture
def engine(settings: Settings) -> Iterator[Engine]:
    engine = build_engine(settings.database_url)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with build_session_factory(engine)() as session:
        yield session


@pytest.fixture
def app(settings: Settings) -> Iterator[FastAPI]:
    application = create_app(settings)
    Base.metadata.create_all(application.state.engine)
    yield application
    Base.metadata.drop_all(application.state.engine)
    application.state.engine.dispose()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def register(client: TestClient) -> Callable[[str], ApiUser]:
    """Cadastra um usuário pela API, faz login e devolve os cabeçalhos autenticados."""

    def _register(name: str = "Ana") -> ApiUser:
        email = f"{name.lower()}@example.com"
        created = client.post("/users", json={"name": name, "email": email, "password": PASSWORD})
        assert created.status_code == 201, created.text
        logged = client.post("/auth/login", json={"email": email, "password": PASSWORD})
        assert logged.status_code == 200, logged.text
        token = logged.json()["access_token"]
        return ApiUser(
            id=created.json()["id"], email=email, headers={"Authorization": f"Bearer {token}"}
        )

    return _register
