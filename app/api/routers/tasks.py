from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

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
from app.domain.entities import TaskPriority, TaskStatus

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
    payload: TaskCreateRequest,
    actor: CurrentUser,
    request: Request,
    response: Response,
    use_case: CreateTaskDep,
) -> TaskResponse:
    task = use_case.execute(actor, payload.to_input())
    response.headers["Location"] = str(request.url_for("get_task", task_id=str(task.id)))
    return TaskResponse.model_validate(task)


@router.get(
    "",
    summary="Listar e filtrar tarefas",
    description=(
        "Todos os filtros são opcionais e combináveis, por exemplo "
        "`/tasks?status=done&priority=high&dueBefore=2026-12-01`. "
        "`dueBefore` e `dueAfter` são exclusivos e ignoram tarefas sem prazo. "
        "O resultado é paginado (`limit`, padrão 50, máximo 100) e ordenado da tarefa mais "
        "recente para a mais antiga."
    ),
)
def list_tasks(
    use_case: ListTasksDep,
    assigned_to: Annotated[
        UUID | None, Query(alias="assignedTo", description="Somente tarefas deste responsável")
    ] = None,
    task_status: Annotated[TaskStatus | None, Query(alias="status")] = None,
    priority: Annotated[TaskPriority | None, Query()] = None,
    due_before: Annotated[
        date | None, Query(alias="dueBefore", description="Prazo anterior a esta data")
    ] = None,
    due_after: Annotated[
        date | None, Query(alias="dueAfter", description="Prazo posterior a esta data")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TaskResponse]:
    filters = TaskFilters(
        assigned_to=assigned_to,
        status=task_status,
        priority=priority,
        due_before=due_before,
        due_after=due_after,
        limit=limit,
        offset=offset,
    )
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
