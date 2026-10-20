from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import (
    CreateTaskDep,
    CurrentUser,
    DeleteTaskDep,
    GetTaskDep,
    ListTasksDep,
    UpdateTaskDep,
    get_current_user,
)
from app.api.schemas.errors import error_responses
from app.api.schemas.tasks import TaskCreateRequest, TaskResponse, TaskUpdateRequest
from app.application.dto import TaskFilters

router = APIRouter(
    prefix="/tasks",
    tags=["Tarefas"],
    dependencies=[Depends(get_current_user)],
    responses=error_responses(401, 422),
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Criar tarefa",
    description="A tarefa é criada como `pending`; quem cria fica registrado como criador.",
)
def create_task(
    payload: TaskCreateRequest, actor: CurrentUser, use_case: CreateTaskDep
) -> TaskResponse:
    return TaskResponse.model_validate(use_case.execute(actor, payload.to_input()))


@router.get(
    "", summary="Listar tarefas", description="Ordenadas da mais recente para a mais antiga."
)
def list_tasks(
    use_case: ListTasksDep,
    assigned_to: Annotated[
        UUID | None, Query(alias="assignedTo", description="Somente tarefas deste responsável")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TaskResponse]:
    filters = TaskFilters(assigned_to=assigned_to, limit=limit, offset=offset)
    return [TaskResponse.model_validate(task) for task in use_case.execute(filters)]


@router.get("/{task_id}", summary="Consultar tarefa", responses=error_responses(404))
def get_task(task_id: UUID, use_case: GetTaskDep) -> TaskResponse:
    return TaskResponse.model_validate(use_case.execute(task_id))


@router.put(
    "/{task_id}",
    summary="Atualizar tarefa",
    description=(
        "Altera título, descrição, status, prioridade, prazo ou responsável. "
        "Permitido ao criador e ao responsável pela tarefa."
    ),
    responses=error_responses(403, 404),
)
def update_task(
    task_id: UUID, payload: TaskUpdateRequest, actor: CurrentUser, use_case: UpdateTaskDep
) -> TaskResponse:
    return TaskResponse.model_validate(use_case.execute(actor, task_id, payload.to_input()))


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover tarefa",
    description="Somente o criador pode remover a tarefa.",
    responses=error_responses(403, 404),
)
def delete_task(task_id: UUID, actor: CurrentUser, use_case: DeleteTaskDep) -> None:
    use_case.execute(actor, task_id)
