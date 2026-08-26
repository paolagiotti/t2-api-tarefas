"""Repository: unico lugar do modulo que fala SQLAlchemy.

O Protocol abaixo e a inversao de dependencia. O service depende do
Protocol (uma interface), nao da classe concreta. No teste unitario da pra
passar um fake em memoria e testar a regra de negocio sem banco nenhum.
"""
import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.models import User


class UserRepositoryProtocol(Protocol):
    def get(self, user_id: uuid.UUID) -> User | None: ...
    def get_by_email(self, email: str) -> User | None: ...
    def add(self, user: User) -> User: ...
    def save(self, user: User) -> User: ...


class SqlAlchemyUserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.scalars(stmt).first()

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()   # gera o id sem fechar a transacao
        return user

    def save(self, user: User) -> User:
        self.db.flush()
        return user
