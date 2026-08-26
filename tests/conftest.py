"""Fixtures compartilhadas.

Truque central: o banco de teste e um SQLite em memoria e a dependency
get_db e sobrescrita. Os testes rodam em segundos, sem Docker, e cada teste
comeca com o banco limpo.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
import app.db.registry  # noqa: F401  garante que todos os models foram carregados


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # mantem a MESMA conexao em memoria
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db_session):
    app = create_app()

    def override_get_db():
        yield db_session
        db_session.commit()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
