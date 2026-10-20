import os
from collections.abc import Iterator

import pytest
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


@pytest.fixture
def settings() -> Settings:
    # _env_file=None garante que o .env de quem roda os testes não interfira.
    return Settings(
        _env_file=None,
        environment="test",
        log_level="WARNING",
        database_url=TEST_DATABASE_URL,
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
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
