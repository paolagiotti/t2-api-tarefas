from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.ports import UserRepository
from app.domain.entities import User
from app.infrastructure.models import UserModel


class SqlAlchemyUserRepository(UserRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user: User) -> None:
        model = UserModel(id=user.id)
        _copy_to_model(user, model)
        self._session.add(model)

    def get(self, user_id: UUID) -> User | None:
        model = self._session.get(UserModel, user_id)
        return _to_entity(model) if model else None

    def get_by_email(self, email: str) -> User | None:
        model = self._session.scalar(select(UserModel).where(UserModel.email == email))
        return _to_entity(model) if model else None

    def save(self, user: User) -> None:
        _copy_to_model(user, self._session.get_one(UserModel, user.id))


def _to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        name=model.name,
        email=model.email,
        password_hash=model.password_hash,
        created_at=model.created_at,
        updated_at=model.updated_at,
        deleted_at=model.deleted_at,
    )


def _copy_to_model(user: User, model: UserModel) -> None:
    model.name = user.name
    model.email = user.email
    model.password_hash = user.password_hash
    model.created_at = user.created_at
    model.updated_at = user.updated_at
    model.deleted_at = user.deleted_at
