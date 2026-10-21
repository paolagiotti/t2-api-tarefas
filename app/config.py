from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuração lida de variáveis de ambiente (e do arquivo .env, se existir)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://tarefas:tarefas@localhost:5432/tarefas"

    jwt_secret: SecretStr = Field(min_length=32)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_expiration_minutes: int = Field(default=60, gt=0)
    bcrypt_rounds: int = Field(default=12, ge=4, le=16)

    # "log" apenas registra o e-mail no log; "smtp" envia de fato (Mailpit no docker-compose).
    notification_backend: Literal["log", "smtp"] = "log"
    email_sender: str = "Gestão de Tarefas <nao-responda@tarefas.example.com>"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    smtp_use_tls: bool = False
    smtp_timeout_seconds: float = Field(default=10, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
