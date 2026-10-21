from app.application.dto import NewTask, TaskChanges
from app.application.use_cases.users import DeleteUser
from app.domain.entities import TaskPriority, TaskStatus
from tests.fakes import SentNotification


def changes(**fields) -> TaskChanges:
    return TaskChanges(**fields, provided=frozenset(fields))


def test_assignee_is_notified_when_task_is_created(make_user, create_task, notifier):
    ana, bruno = make_user(name="Ana"), make_user(name="Bruno")

    task = create_task.execute(ana, NewTask(title="Revisar", assigned_to=bruno.id))

    assert notifier.sent == [SentNotification("assigned", task.id, bruno.id, ana.id)]


def test_no_notification_for_unassigned_or_self_assigned_task(make_user, create_task, notifier):
    ana = make_user(name="Ana")

    create_task.execute(ana, NewTask(title="Sem responsável"))
    create_task.execute(ana, NewTask(title="Para mim", assigned_to=ana.id))

    assert notifier.sent == []


def test_creator_is_notified_when_assignee_completes_task(
    make_user, create_task, update_task, notifier
):
    ana, bruno = make_user(name="Ana"), make_user(name="Bruno")
    task = create_task.execute(ana, NewTask(title="Revisar", assigned_to=bruno.id))
    notifier.sent.clear()

    update_task.execute(bruno, task.id, changes(status=TaskStatus.DONE))

    assert notifier.sent == [SentNotification("updated", task.id, ana.id, bruno.id, ("status",))]


def test_assignee_is_notified_when_creator_changes_task(
    make_user, create_task, update_task, notifier
):
    ana, bruno = make_user(name="Ana"), make_user(name="Bruno")
    task = create_task.execute(ana, NewTask(title="Revisar", assigned_to=bruno.id))
    notifier.sent.clear()

    update_task.execute(ana, task.id, changes(priority=TaskPriority.HIGH, title="Revisar já"))

    assert notifier.sent == [
        SentNotification("updated", task.id, bruno.id, ana.id, ("title", "priority"))
    ]


def test_reassignment_notifies_new_assignee_and_creator(
    make_user, create_task, update_task, notifier
):
    ana, bruno, carla = make_user(name="Ana"), make_user(name="Bruno"), make_user(name="Carla")
    task = create_task.execute(ana, NewTask(title="Revisar", assigned_to=bruno.id))
    notifier.sent.clear()

    update_task.execute(bruno, task.id, changes(assigned_to=carla.id))

    assert notifier.sent == [
        SentNotification("assigned", task.id, carla.id, bruno.id),
        SentNotification("updated", task.id, ana.id, bruno.id, ("assigned_to",)),
    ]


def test_no_notification_when_nothing_changes(make_user, create_task, update_task, notifier):
    ana, bruno = make_user(name="Ana"), make_user(name="Bruno")
    task = create_task.execute(ana, NewTask(title="Revisar", assigned_to=bruno.id))
    notifier.sent.clear()

    update_task.execute(ana, task.id, changes(title="Revisar"))

    assert notifier.sent == []


def test_deactivated_users_are_not_notified(uow, make_user, create_task, update_task, notifier):
    ana, bruno = make_user(name="Ana"), make_user(name="Bruno")
    task = create_task.execute(ana, NewTask(title="Revisar", assigned_to=bruno.id))
    DeleteUser(uow).execute(ana, ana.id)
    notifier.sent.clear()

    update_task.execute(bruno, task.id, changes(status=TaskStatus.IN_PROGRESS))

    assert notifier.sent == []
