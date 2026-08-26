"""Importa todos os models para o Alembic enxergar.

Sem isso, `alembic revision --autogenerate` gera uma migration vazia.
Toda vez que um modulo novo ganhar um model, adicione o import aqui.
"""
from app.db.base import Base  # noqa: F401
from app.modules.tasks.models import Task  # noqa: F401
from app.modules.users.models import User  # noqa: F401
