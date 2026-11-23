import logging
from dataclasses import replace
from uuid import UUID

from app.application.dto import NewTask, TaskChanges, TaskFilters
from app.application.ports import TaskNotifier, UnitOfWork
from app.domain.entities import Task, User
from app.domain.exceptions import BusinessRuleViolation, NotFoundError, PermissionDeniedError

logger = logging.getLogger(__name__)

TRACKED_FIELDS = ("title", "description", "status", "priority", "due_date", "assigned_to")


class CreateTask:
    def __init__(self, uow: UnitOfWork, notifier: TaskNotifier) -> None:
        self._uow = uow
        self._notifier = notifier

    def execute(self, actor: User, data: NewTask) -> Task:
        assignee = None
        if data.assigned_to is not None:
            assignee = _get_assignable_user(self._uow, data.assigned_to)

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

        if assignee is not None and assignee.id != actor.id:
            self._notifier.task_assigned(task, assignee, actor)
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
    def __init__(self, uow: UnitOfWork, notifier: TaskNotifier) -> None:
        self._uow = uow
        self._notifier = notifier

    def execute(self, actor: User, task_id: UUID, changes: TaskChanges) -> Task:
        task = _get_task(self._uow, task_id)
        if not (task.can_be_edited_by(actor.id) or _creator_left(self._uow, task)):
            raise PermissionDeniedError("Apenas o criador ou o responsável podem alterar a tarefa")

        before = replace(task)
        new_assignee = self._apply(task, changes)
        changed = [name for name in TRACKED_FIELDS if getattr(task, name) != getattr(before, name)]
        if not changed:
            return task

        task.touch()
        self._uow.tasks.save(task)
        self._uow.commit()
        logger.info("Tarefa %s alterada por %s: %s", task.id, actor.id, ", ".join(changed))

        self._notify(task, actor, changed, new_assignee, previous_assignee=before.assigned_to)
        return task

    def _apply(self, task: Task, changes: TaskChanges) -> User | None:
        """Aplica as alterações e devolve o novo responsável, quando a tarefa é reatribuída."""
        if changes.title is not None:
            task.rename(changes.title)
        if changes.status is not None:
            task.change_status(changes.status)
        if changes.priority is not None:
            task.priority = changes.priority
        if changes.has("description"):
            task.describe(changes.description)
        if changes.has("due_date"):
            task.due_date = changes.due_date

        new_assignee = None
        if changes.has("assigned_to") and changes.assigned_to != task.assigned_to:
            if changes.assigned_to is not None:
                new_assignee = _get_assignable_user(self._uow, changes.assigned_to)
            task.assign_to(changes.assigned_to)
        return new_assignee

    def _notify(
        self,
        task: Task,
        actor: User,
        changed: list[str],
        new_assignee: User | None,
        previous_assignee: UUID | None,
    ) -> None:
        """O novo responsável recebe o aviso de atribuição. Criador, responsável e, quando a
        tarefa troca de mãos, o responsável anterior recebem o aviso de alteração. Quem fez a
        alteração não é notificado."""
        notified = {actor.id}
        if new_assignee is not None and new_assignee.id not in notified:
            self._notifier.task_assigned(task, new_assignee, actor)
            notified.add(new_assignee.id)

        for user_id in (task.created_by, task.assigned_to, previous_assignee):
            if user_id is None or user_id in notified:
                continue
            notified.add(user_id)
            recipient = self._uow.users.get(user_id)
            if recipient is not None and recipient.is_active:
                self._notifier.task_updated(task, recipient, actor, changed)


class DeleteTask:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, actor: User, task_id: UUID) -> None:
        task = _get_task(self._uow, task_id)
        if not (task.can_be_deleted_by(actor.id) or _creator_left(self._uow, task)):
            raise PermissionDeniedError("Apenas o criador pode remover a tarefa")

        self._uow.tasks.delete(task)
        self._uow.commit()
        logger.info("Tarefa %s removida por %s", task.id, actor.id)


def _get_task(uow: UnitOfWork, task_id: UUID) -> Task:
    task = uow.tasks.get(task_id)
    if task is None:
        raise NotFoundError("Tarefa não encontrada")
    return task


def _creator_left(uow: UnitOfWork, task: Task) -> bool:
    """Quando o criador é removido, a tarefa passa a ser da equipe: qualquer usuário pode
    editá-la ou removê-la, para que ela não fique sem ninguém que possa cuidar dela."""
    creator = uow.users.get(task.created_by)
    return creator is None or not creator.is_active


def _get_assignable_user(uow: UnitOfWork, user_id: UUID) -> User:
    user = uow.users.get(user_id)
    if user is None or not user.is_active:
        raise BusinessRuleViolation("O responsável informado não existe ou foi removido")
    return user
