"""Router: traduz HTTP <-> service. Sem regra de negocio aqui dentro."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.users.repository import SqlAlchemyUserRepository
from app.modules.users.schemas import UserCreate, UserRead, UserUpdate
from app.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(db: Annotated[Session, Depends(get_db)]) -> UserService:
    """Montagem da cadeia: sessao -> repository -> service."""
    return UserService(SqlAlchemyUserRepository(db))


ServiceDep = Annotated[UserService, Depends(get_user_service)]


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, service: ServiceDep):
    return service.create(payload)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: uuid.UUID, service: ServiceDep):
    return service.get(user_id)


@router.put("/{user_id}", response_model=UserRead)
def update_user(user_id: uuid.UUID, payload: UserUpdate, service: ServiceDep):
    return service.update(user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: uuid.UUID, service: ServiceDep):
    service.soft_delete(user_id)
