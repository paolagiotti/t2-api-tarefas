import logging
from dataclasses import replace
from uuid import UUID

from app.application.dto import NewTask, TaskChanges, TaskFilters
from app.application.ports import UnitOfWork
from app.domain.entities import Task, User
from app.domain.exceptions import BusinessRuleViolation, NotFoundError, PermissionDeniedError

logger = logging.getLogger(__name__)

TRACKED_FIELDS = ("title", "description", "status", "priority", "due_date", "assigned_to")


class CreateTask:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, actor: User, data: NewTask) -> Task:
        if data.assigned_to is not None:
            _get_assignable_user(self._uow, data.assigned_to)

        task = Task(
            title=data.title,
            description=data.description,
            priority=data.priority,
            due_date=data.due_date,
            assigned_to=data.assigned_to,
            created_by=actor.id,
        )
        self._uow.tasks.add(task)
        self._uow.commit()
        logger.info("Tarefa %s criada por %s", task.id, actor.id)
        return task


class GetTask:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, task_id: UUID) -> Task:
        return _get_task(self._uow, task_id)


class ListTasks:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, filters: TaskFilters) -> list[Task]:
        return self._uow.tasks.find(filters)


class UpdateTask:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, actor: User, task_id: UUID, changes: TaskChanges) -> Task:
        task = _get_task(self._uow, task_id)
        if not task.can_be_edited_by(actor.id):
            raise PermissionDeniedError("Apenas o criador ou o responsável podem alterar a tarefa")

        before = replace(task)
        self._apply(task, changes)
        changed = [name for name in TRACKED_FIELDS if getattr(task, name) != getattr(before, name)]
        if not changed:
            return task

        task.touch()
        self._uow.tasks.save(task)
        self._uow.commit()
        logger.info("Tarefa %s alterada por %s: %s", task.id, actor.id, ", ".join(changed))
        return task

    def _apply(self, task: Task, changes: TaskChanges) -> None:
        if changes.title is not None:
            task.rename(changes.title)
        if changes.status is not None:
            task.change_status(changes.status)
        if changes.priority is not None:
            task.priority = changes.priority
        if changes.has("description"):
            task.description = changes.description
        if changes.has("due_date"):
            task.due_date = changes.due_date
        if changes.has("assigned_to") and changes.assigned_to != task.assigned_to:
            if changes.assigned_to is not None:
                _get_assignable_user(self._uow, changes.assigned_to)
            task.assign_to(changes.assigned_to)


class DeleteTask:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, actor: User, task_id: UUID) -> None:
        task = _get_task(self._uow, task_id)
        if not task.can_be_deleted_by(actor.id):
            raise PermissionDeniedError("Apenas o criador pode remover a tarefa")

        self._uow.tasks.delete(task)
        self._uow.commit()
        logger.info("Tarefa %s removida por %s", task.id, actor.id)


def _get_task(uow: UnitOfWork, task_id: UUID) -> Task:
    task = uow.tasks.get(task_id)
    if task is None:
        raise NotFoundError("Tarefa não encontrada")
    return task


def _get_assignable_user(uow: UnitOfWork, user_id: UUID) -> User:
    user = uow.users.get(user_id)
    if user is None or not user.is_active:
        raise BusinessRuleViolation("O responsável informado não existe ou foi removido")
    return user
