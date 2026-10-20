from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator
from pydantic.alias_generators import to_camel

from app.api.schemas.base import ApiSchema
from app.application.dto import NewTask, TaskChanges
from app.domain.entities import TaskPriority, TaskStatus


class TaskCreateRequest(ApiSchema):
    title: str = Field(min_length=1, max_length=200, examples=["Gravar o vídeo de demonstração"])
    description: str | None = Field(default=None, max_length=5000)
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


class TaskUpdateRequest(ApiSchema):
    """Atualização parcial: somente os campos enviados mudam.

    Envie `null` em `description`, `dueDate` ou `assignedTo` para limpar o valor.
    """

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None
    assigned_to: UUID | None = None

    @model_validator(mode="after")
    def reject_null_in_required_fields(self) -> Self:
        for name in ("title", "status", "priority"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"o campo {to_camel(name)} não pode ser nulo")
        return self

    def to_input(self) -> TaskChanges:
        data = self.model_dump(exclude_unset=True)
        return TaskChanges(**data, provided=frozenset(data))


class TaskResponse(ApiSchema):
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
