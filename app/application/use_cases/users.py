import logging
from dataclasses import replace
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
PASSWORD_MAX_LENGTH = 128


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

        new_email = normalize_email(changes.email) if changes.email is not None else user.email
        if new_email != user.email or changes.password is not None:
            # Trocar credenciais exige a senha atual: um token roubado não basta.
            self._confirm_current_password(user, changes.current_password)

        before = replace(user)
        if changes.name is not None:
            user.rename(changes.name)
        if new_email != user.email:
            _ensure_email_available(self._uow, new_email)
            user.change_email(new_email)
        if changes.password is not None:
            _ensure_valid_password(changes.password)
            user.password_hash = self._hasher.hash(changes.password)
        if user == before:
            return user

        user.touch()
        self._uow.users.save(user)
        self._uow.commit()
        logger.info("Usuário %s atualizado", user.id)
        return user

    def _confirm_current_password(self, user: User, current_password: str | None) -> None:
        if current_password is None:
            raise BusinessRuleViolation("Informe a senha atual para alterar e-mail ou senha")
        if not self._hasher.verify(current_password, user.password_hash):
            raise PermissionDeniedError("Senha atual incorreta")


class DeleteUser:
    """Desativa o usuário e libera as tarefas em aberto sob sua responsabilidade."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, actor: User, user_id: UUID) -> None:
        _ensure_same_user(actor, user_id, action="remover")
        user = get_active_user(self._uow, user_id)

        user.deactivate()
        self._uow.users.save(user)
        released = self._uow.tasks.list_open_assigned_to(user.id)
        for task in released:
            task.assign_to(None)
            task.touch()
            self._uow.tasks.save(task)
        self._uow.commit()
        logger.info(
            "Usuário %s desativado (soft delete); %d tarefa(s) em aberto ficaram sem responsável",
            user.id,
            len(released),
        )


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
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        raise BusinessRuleViolation(
            f"A senha deve ter entre {PASSWORD_MIN_LENGTH} e {PASSWORD_MAX_LENGTH} caracteres"
        )
