from datetime import date, datetime
from uuid import UUID

from pydantic import Field, field_validator

from app.api.schemas.base import RequestSchema, ResponseSchema, reject_null
from app.application.dto import NewTask, TaskChanges
from app.domain.entities import (
    TASK_DESCRIPTION_MAX_LENGTH,
    TASK_TITLE_MAX_LENGTH,
    TaskPriority,
    TaskStatus,
)


class TaskCreateRequest(RequestSchema):
    title: str = Field(
        min_length=1, max_length=TASK_TITLE_MAX_LENGTH, examples=["Gravar o vídeo de demonstração"]
    )
    description: str | None = Field(default=None, max_length=TASK_DESCRIPTION_MAX_LENGTH)
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = Field(default=None, examples=["2026-11-30"])
    assigned_to: UUID | None = Field(default=None, description="Usuário responsável")

    def to_input(self) -> NewTask:
        return NewTask(
            title=self.title,
            description=self.description,
            priority=self.priority,
            due_date=self.due_date,
            assigned_to=self.assigned_to,
        )


class TaskUpdateRequest(RequestSchema):
    """Atualização parcial: somente os campos enviados mudam.

    Envie `null` em `description`, `dueDate` ou `assignedTo` para limpar o valor; `title`,
    `status` e `priority` não aceitam `null`.
    """

    title: str | None = Field(default=None, min_length=1, max_length=TASK_TITLE_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=TASK_DESCRIPTION_MAX_LENGTH)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None
    assigned_to: UUID | None = None

    _not_null = field_validator("title", "status", "priority", mode="before")(reject_null)

    def to_input(self) -> TaskChanges:
        data = self.model_dump(exclude_unset=True)
        return TaskChanges(**data, provided=frozenset(data))


class TaskResponse(ResponseSchema):
    id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    assigned_to: UUID | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
