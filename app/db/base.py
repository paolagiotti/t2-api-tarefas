"""Base declarativa do SQLAlchemy + mixins compartilhados.

IMPORTANTE: todo model precisa ser importado em algum lugar antes do Alembic
rodar o autogenerate, senao a tabela nao aparece na migration. Por isso
existe o app/db/registry.py.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """created_at / updated_at automaticos, preenchidos pelo banco."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()
