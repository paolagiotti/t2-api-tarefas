from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.dependencies import (
    CreateUserDep,
    CurrentUser,
    DeleteUserDep,
    GetUserDep,
    UpdateUserDep,
    get_current_user,
)
from app.api.schemas.errors import error_responses
from app.api.schemas.users import UserCreateRequest, UserResponse, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["Usuários"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Criar usuário",
    description="Cadastro público. A senha é armazenada apenas como hash (bcrypt).",
    responses=error_responses(409, 422),
)
def create_user(
    payload: UserCreateRequest, request: Request, response: Response, use_case: CreateUserDep
) -> UserResponse:
    user = use_case.execute(payload.to_input())
    response.headers["Location"] = str(request.url_for("get_user", user_id=str(user.id)))
    return UserResponse.model_validate(user)


@router.get(
    "/{user_id}",
    summary="Consultar usuário",
    dependencies=[Depends(get_current_user)],
    responses=error_responses(401, 404, 422),
)
def get_user(user_id: UUID, use_case: GetUserDep) -> UserResponse:
    return UserResponse.model_validate(use_case.execute(user_id))


@router.put(
    "/{user_id}",
    summary="Atualizar usuário",
    description="Somente o próprio usuário altera o seu cadastro. Campos omitidos não mudam.",
    responses=error_responses(401, 403, 404, 409, 422),
)
def update_user(
    user_id: UUID, payload: UserUpdateRequest, actor: CurrentUser, use_case: UpdateUserDep
) -> UserResponse:
    return UserResponse.model_validate(use_case.execute(actor, user_id, payload.to_input()))


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover usuário",
    description=(
        "Remoção lógica (soft delete): o usuário deixa de aparecer e de autenticar, mas o "
        "registro é mantido para preservar a autoria das tarefas."
    ),
    responses=error_responses(401, 403, 404, 422),
)
def delete_user(user_id: UUID, actor: CurrentUser, use_case: DeleteUserDep) -> None:
    use_case.execute(actor, user_id)
