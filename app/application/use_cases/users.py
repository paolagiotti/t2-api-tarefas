import logging
from uuid import UUID

from app.application.dto import NewUser, UserChanges
from app.application.ports import PasswordHasher, UnitOfWork
from app.domain.entities import User, normalize_email
from app.domain.exceptions import (
    BusinessRuleViolation,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)

logger = logging.getLogger(__name__)

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_BYTES = 72  # limite do algoritmo bcrypt


class CreateUser:
    def __init__(self, uow: UnitOfWork, hasher: PasswordHasher) -> None:
        self._uow = uow
        self._hasher = hasher

    def execute(self, data: NewUser) -> User:
        email = normalize_email(data.email)
        _ensure_email_available(self._uow, email)
        _ensure_valid_password(data.password)

        user = User(name=data.name, email=email, password_hash=self._hasher.hash(data.password))
        self._uow.users.add(user)
        self._uow.commit()
        logger.info("Usuário %s criado", user.id)
        return user


class GetUser:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, user_id: UUID) -> User:
        return get_active_user(self._uow, user_id)


class UpdateUser:
    def __init__(self, uow: UnitOfWork, hasher: PasswordHasher) -> None:
        self._uow = uow
        self._hasher = hasher

    def execute(self, actor: User, user_id: UUID, changes: UserChanges) -> User:
        _ensure_same_user(actor, user_id, action="alterar")
        user = get_active_user(self._uow, user_id)

        if changes.name is not None:
            user.rename(changes.name)
        if changes.email is not None:
            email = normalize_email(changes.email)
            if email != user.email:
                _ensure_email_available(self._uow, email)
                user.email = email
        if changes.password is not None:
            _ensure_valid_password(changes.password)
            user.password_hash = self._hasher.hash(changes.password)

        user.touch()
        self._uow.users.save(user)
        self._uow.commit()
        logger.info("Usuário %s atualizado", user.id)
        return user


class DeleteUser:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, actor: User, user_id: UUID) -> None:
        _ensure_same_user(actor, user_id, action="remover")
        user = get_active_user(self._uow, user_id)

        user.deactivate()
        self._uow.users.save(user)
        self._uow.commit()
        logger.info("Usuário %s desativado (soft delete)", user.id)


def get_active_user(uow: UnitOfWork, user_id: UUID) -> User:
    user = uow.users.get(user_id)
    if user is None or not user.is_active:
        raise NotFoundError("Usuário não encontrado")
    return user


def _ensure_same_user(actor: User, user_id: UUID, action: str) -> None:
    if actor.id != user_id:
        raise PermissionDeniedError(f"Você só pode {action} o seu próprio cadastro")


def _ensure_email_available(uow: UnitOfWork, email: str) -> None:
    if uow.users.get_by_email(email) is not None:
        raise ConflictError("Já existe um usuário cadastrado com este e-mail")


def _ensure_valid_password(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise BusinessRuleViolation(f"A senha deve ter pelo menos {PASSWORD_MIN_LENGTH} caracteres")
    if len(password.encode()) > PASSWORD_MAX_BYTES:
        raise BusinessRuleViolation(f"A senha deve ter no máximo {PASSWORD_MAX_BYTES} bytes")
