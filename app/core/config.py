"""Configuracao central da aplicacao.

Regra: NENHUM outro arquivo le os.environ diretamente. Todo mundo importa
get_settings(). Isso deixa a configuracao testavel (da pra sobrescrever)
e documenta num lugar so tudo que o sistema precisa pra subir.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "API de Gestao de Tarefas Colaborativas"
    debug: bool = False

    # Banco
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/tarefas"

    # Seguranca (Pessoa A usa isso)
    jwt_secret: str = "troque-isso-em-producao"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60


@lru_cache
def get_settings() -> Settings:
    """Cacheado: le o .env uma vez so por processo."""
    return Settings()
