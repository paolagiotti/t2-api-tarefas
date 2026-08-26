"""Service: a regra de negocio.

Repare no que ESTE arquivo nao importa: nada de fastapi, nada de sqlalchemy.
Esse e o teste pratico de que a arquitetura esta desacoplada — e o argumento
principal da secao "Decisoes Arquiteturais" da documentacao.
"""
import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password
from app.modules.users.models import User
from app.modules.users.repository import UserRepositoryProtocol
from app.modules.users.schemas import UserCreate, UserUpdate


class UserService:
    def __init__(self, repo: UserRepositoryProtocol):
        self.repo = repo

    def create(self, data: UserCreate) -> User:
        if self.repo.get_by_email(data.email):
            raise ConflictError("Ja existe um usuario com esse e-mail.")
        user = User(
            name=data.name,
            email=data.email,
            password_hash=hash_password(data.password),
            role=data.role,
        )
        return self.repo.add(user)

    def get(self, user_id: uuid.UUID) -> User:
        user = self.repo.get(user_id)
        if user is None or not user.is_active:
            raise NotFoundError("Usuario nao encontrado.")
        return user

    def update(self, user_id: uuid.UUID, data: UserUpdate) -> User:
        user = self.get(user_id)
        if data.email and data.email != user.email:
            if self.repo.get_by_email(data.email):
                raise ConflictError("E-mail ja utilizado por outro usuario.")
            user.email = data.email
        if data.name:
            user.name = data.name
        return self.repo.save(user)

    def soft_delete(self, user_id: uuid.UUID) -> None:
        user = self.get(user_id)
        user.is_active = False
        self.repo.save(user)
