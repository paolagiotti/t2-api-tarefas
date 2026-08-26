"""Engine, fabrica de sessoes e a dependency get_db.

get_db e o unico ponto onde uma Session nasce e morre. Uma sessao por
requisicao: abre no inicio, commita se deu certo, faz rollback se estourou
excecao, e fecha sempre.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # testa a conexao antes de usar (evita conexao zumbi)
    echo=settings.debug,  # loga o SQL gerado quando DEBUG=true
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,  # objetos continuam utilizaveis depois do commit
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
