from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.dto import TaskFilters
from app.application.ports import TaskRepository
from app.domain.entities import Task, TaskPriority, TaskStatus
from app.infrastructure.models import TaskModel


class SqlAlchemyTaskRepository(TaskRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, task: Task) -> None:
        model = TaskModel(id=task.id)
        _copy_to_model(task, model)
        self._session.add(model)

    def get(self, task_id: UUID) -> Task | None:
        model = self._session.get(TaskModel, task_id)
        return _to_entity(model) if model else None

    def save(self, task: Task) -> None:
        _copy_to_model(task, self._session.get_one(TaskModel, task.id))

    def delete(self, task: Task) -> None:
        self._session.delete(self._session.get_one(TaskModel, task.id))

    def find(self, filters: TaskFilters) -> list[Task]:
        query = select(TaskModel)
        if filters.assigned_to is not None:
            query = query.where(TaskModel.assigned_to == filters.assigned_to)

        query = (
            query.order_by(TaskModel.created_at.desc(), TaskModel.id)
            .limit(filters.limit)
            .offset(filters.offset)
        )
        return [_to_entity(model) for model in self._session.scalars(query)]


def _to_entity(model: TaskModel) -> Task:
    return Task(
        id=model.id,
        title=model.title,
        description=model.description,
        status=TaskStatus(model.status),
        priority=TaskPriority(model.priority),
        due_date=model.due_date,
        created_by=model.created_by,
        assigned_to=model.assigned_to,
        created_at=model.created_at,
        updated_at=model.updated_at,
        completed_at=model.completed_at,
    )


def _copy_to_model(task: Task, model: TaskModel) -> None:
    model.title = task.title
    model.description = task.description
    model.status = task.status.value
    model.priority = task.priority.value
    model.due_date = task.due_date
    model.created_by = task.created_by
    model.assigned_to = task.assigned_to
    model.created_at = task.created_at
    model.updated_at = task.updated_at
    model.completed_at = task.completed_at
