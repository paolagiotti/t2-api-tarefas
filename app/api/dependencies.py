"""Injeção de dependências da camada HTTP.

Cada provedor monta um caso de uso com as implementações concretas das suas portas. Os routers
só declaram de qual caso de uso precisam, sem saber como ele é construído.
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.application.dto import Principal
from app.application.ports import PasswordHasher, TokenService, UnitOfWork
from app.application.use_cases.auth import AuthenticateToken, Login, Logout
from app.application.use_cases.tasks import CreateTask, DeleteTask, GetTask, ListTasks, UpdateTask
from app.application.use_cases.users import CreateUser, DeleteUser, GetUser, UpdateUser
from app.domain.entities import User
from app.domain.exceptions import AuthenticationError
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork

bearer_scheme = HTTPBearer(auto_error=False, description="Token JWT obtido em `POST /auth/login`.")


# Infraestrutura


def get_session(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_unit_of_work(session: Annotated[Session, Depends(get_session)]) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session)


def get_password_hasher(request: Request) -> PasswordHasher:
    return request.app.state.password_hasher


def get_token_service(request: Request) -> TokenService:
    return request.app.state.token_service


UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]
PasswordHasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]
TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]


# Autenticação


def _authenticate_token(uow: UnitOfWorkDep, tokens: TokenServiceDep) -> AuthenticateToken:
    return AuthenticateToken(uow, tokens)


def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    authenticate: Annotated[AuthenticateToken, Depends(_authenticate_token)],
) -> Principal:
    if credentials is None:
        raise AuthenticationError("Token de acesso não informado")
    return authenticate.execute(credentials.credentials)


def get_current_user(principal: Annotated[Principal, Depends(get_principal)]) -> User:
    return principal.user


CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _login(uow: UnitOfWorkDep, hasher: PasswordHasherDep, tokens: TokenServiceDep) -> Login:
    return Login(uow, hasher, tokens)


def _logout(uow: UnitOfWorkDep) -> Logout:
    return Logout(uow)


LoginDep = Annotated[Login, Depends(_login)]
LogoutDep = Annotated[Logout, Depends(_logout)]


# Usuários


def _create_user(uow: UnitOfWorkDep, hasher: PasswordHasherDep) -> CreateUser:
    return CreateUser(uow, hasher)


def _get_user(uow: UnitOfWorkDep) -> GetUser:
    return GetUser(uow)


def _update_user(uow: UnitOfWorkDep, hasher: PasswordHasherDep) -> UpdateUser:
    return UpdateUser(uow, hasher)


def _delete_user(uow: UnitOfWorkDep) -> DeleteUser:
    return DeleteUser(uow)


CreateUserDep = Annotated[CreateUser, Depends(_create_user)]
GetUserDep = Annotated[GetUser, Depends(_get_user)]
UpdateUserDep = Annotated[UpdateUser, Depends(_update_user)]
DeleteUserDep = Annotated[DeleteUser, Depends(_delete_user)]


# Tarefas


def _create_task(uow: UnitOfWorkDep) -> CreateTask:
    return CreateTask(uow)


def _get_task(uow: UnitOfWorkDep) -> GetTask:
    return GetTask(uow)


def _list_tasks(uow: UnitOfWorkDep) -> ListTasks:
    return ListTasks(uow)


def _update_task(uow: UnitOfWorkDep) -> UpdateTask:
    return UpdateTask(uow)


def _delete_task(uow: UnitOfWorkDep) -> DeleteTask:
    return DeleteTask(uow)


CreateTaskDep = Annotated[CreateTask, Depends(_create_task)]
GetTaskDep = Annotated[GetTask, Depends(_get_task)]
ListTasksDep = Annotated[ListTasks, Depends(_list_tasks)]
UpdateTaskDep = Annotated[UpdateTask, Depends(_update_task)]
DeleteTaskDep = Annotated[DeleteTask, Depends(_delete_task)]
