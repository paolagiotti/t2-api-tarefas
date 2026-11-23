from datetime import date
from uuid import uuid4

import pytest

from app.application.dto import NewTask, TaskChanges, TaskFilters
from app.application.use_cases.tasks import DeleteTask, GetTask, ListTasks
from app.application.use_cases.users import DeleteUser
from app.domain.entities import TaskPriority, TaskStatus
from app.domain.exceptions import BusinessRuleViolation, NotFoundError, PermissionDeniedError


def changes(**fields) -> TaskChanges:
    return TaskChanges(**fields, provided=frozenset(fields))


def test_create_task_records_creator_and_defaults(uow, make_user, create_task):
    ana = make_user()

    task = create_task.execute(ana, NewTask(title="Montar slides"))

    stored = uow.tasks.get(task.id)
    assert stored.created_by == ana.id
    assert stored.status == TaskStatus.PENDING
    assert stored.priority == TaskPriority.MEDIUM
    assert stored.assigned_to is None
    assert uow.commits == 1


def test_create_task_with_assignee(uow, make_user, create_task):
    ana, bruno = make_user(name="Ana"), make_user(name="Bruno")

    task = create_task.execute(ana, NewTask(title="Gravar vídeo", assigned_to=bruno.id))

    assert uow.tasks.get(task.id).assigned_to == bruno.id


def test_create_task_rejects_unknown_assignee(uow, make_user, create_task):
    with pytest.raises(BusinessRuleViolation):
        create_task.execute(make_user(), NewTask(title="Gravar vídeo", assigned_to=uuid4()))
    assert uow.commits == 0


def test_create_task_rejects_deactivated_assignee(uow, make_user, create_task):
    ana, bruno = make_user(name="Ana"), make_user(name="Bruno")
    DeleteUser(uow).execute(bruno, bruno.id)

    with pytest.raises(BusinessRuleViolation):
        create_task.execute(ana, NewTask(title="Gravar vídeo", assigned_to=bruno.id))


def test_get_task_raises_not_found_for_unknown_id(uow):
    with pytest.raises(NotFoundError):
        GetTask(uow).execute(uuid4())


def test_list_tasks_filters_by_assignee(uow, make_user, create_task):
    ana, bruno = make_user(name="Ana"), make_user(name="Bruno")
    create_task.execute(ana, NewTask(title="Da Ana", assigned_to=ana.id))
    create_task.execute(ana, NewTask(title="Do Bruno", assigned_to=bruno.id))

    tasks = ListTasks(uow).execute(TaskFilters(assigned_to=bruno.id))

    assert [task.title for task in tasks] == ["Do Bruno"]


def test_creator_updates_task_fields(uow, make_user, create_task, update_task):
    ana = make_user()
    task = create_task.execute(ana, NewTask(title="Rascunho"))

    update_task.execute(
        ana,
        task.id,
        changes(title="Versão final", priority=TaskPriority.HIGH, due_date=date(2026, 11, 30)),
    )

    stored = uow.tasks.get(task.id)
    assert stored.title == "Versão final"
    assert stored.priority == TaskPriority.HIGH
    assert stored.due_date == date(2026, 11, 30)
    assert stored.updated_at >= task.updated_at


def test_assignee_can_complete_task(uow, make_user, create_task, update_task):
    ana, bruno = make_user(name="Ana"), make_user(name="Bruno")
    task = create_task.execute(ana, NewTask(title="Revisar", assigned_to=bruno.id))

    update_task.execute(bruno, task.id, changes(status=TaskStatus.DONE))

    stored = uow.tasks.get(task.id)
    assert stored.status == TaskStatus.DONE
    assert stored.completed_at is not None


def test_other_users_cannot_update_task(make_user, create_task, update_task):
    ana, carla = make_user(name="Ana"), make_user(name="Carla")
    task = create_task.execute(ana, NewTask(title="Revisar"))

    with pytest.raises(PermissionDeniedError):
        update_task.execute(carla, task.id, changes(title="Hackeada"))


def test_update_can_clear_optional_fields(uow, make_user, create_task, update_task):
    ana = make_user()
    task = create_task.execute(
        ana,
        NewTask(
            title="Revisar",
            description="Ver ortografia",
            due_date=date(2026, 12, 1),
            assigned_to=ana.id,
        ),
    )

    update_task.execute(ana, task.id, changes(description=None, due_date=None, assigned_to=None))

    stored = uow.tasks.get(task.id)
    assert stored.description is None
    assert stored.due_date is None
    assert stored.assigned_to is None


def test_update_without_effective_changes_does_not_commit(uow, make_user, create_task, update_task):
    ana = make_user()
    task = create_task.execute(ana, NewTask(title="Revisar"))

    update_task.execute(ana, task.id, changes(title="Revisar"))

    assert uow.commits == 1


def test_update_rejects_unknown_assignee(make_user, create_task, update_task):
    ana = make_user()
    task = create_task.execute(ana, NewTask(title="Revisar"))

    with pytest.raises(BusinessRuleViolation):
        update_task.execute(ana, task.id, changes(assigned_to=uuid4()))


def test_creator_deletes_task(uow, make_user, create_task):
    ana = make_user()
    task = create_task.execute(ana, NewTask(title="Temporária"))

    DeleteTask(uow).execute(ana, task.id)

    assert uow.tasks.get(task.id) is None


def test_team_takes_over_tasks_of_a_removed_creator(uow, make_user, create_task, update_task):
    ana, bruno = make_user(name="Ana"), make_user(name="Bruno")
    task = create_task.execute(ana, NewTask(title="Da Ana", assigned_to=ana.id))
    DeleteUser(uow).execute(ana, ana.id)

    update_task.execute(bruno, task.id, changes(assigned_to=bruno.id))
    DeleteTask(uow).execute(bruno, task.id)

    assert uow.tasks.get(task.id) is None


def test_assignee_cannot_delete_task(uow, make_user, create_task):
    ana, bruno = make_user(name="Ana"), make_user(name="Bruno")
    task = create_task.execute(ana, NewTask(title="Importante", assigned_to=bruno.id))

    with pytest.raises(PermissionDeniedError):
        DeleteTask(uow).execute(bruno, task.id)
    assert uow.tasks.get(task.id) is not None
