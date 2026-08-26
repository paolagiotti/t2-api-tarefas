"""Schemas Pydantic: o contrato HTTP (entrada e saida).

Existem SEPARADOS do model porque o que entra pela API nao e o que fica no
banco. UserCreate recebe `password` em texto puro; UserRead nunca devolve
`password_hash`. Se usassemos o model direto na resposta, um campo novo no
banco vazaria pra API sem ninguem perceber.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.users.models import UserRole


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: UserRole = UserRole.USER


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None


class UserRead(BaseModel):
    # from_attributes permite construir a partir do objeto ORM.
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
