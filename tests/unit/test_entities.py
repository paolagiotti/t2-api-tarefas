from uuid import uuid4

import pytest

from app.domain.entities import Task, TaskPriority, TaskStatus, User, normalize_email
from app.domain.exceptions import BusinessRuleViolation


def make_task(**overrides) -> Task:
    data = {"title": "Revisar documentação", "created_by": uuid4()}
    data.update(overrides)
    return Task(**data)


def make_user(**overrides) -> User:
    data = {"name": "Ana", "email": "ana@example.com", "password_hash": "hash"}
    data.update(overrides)
    return User(**data)


def test_new_task_starts_pending_with_medium_priority():
    task = make_task()

    assert task.status == TaskStatus.PENDING
    assert task.priority == TaskPriority.MEDIUM
    assert task.completed_at is None


def test_task_title_is_trimmed():
    assert make_task(title="  Revisar slides  ").title == "Revisar slides"


@pytest.mark.parametrize("title", ["", "   ", "x" * 201])
def test_task_rejects_invalid_title(title):
    with pytest.raises(BusinessRuleViolation):
        make_task(title=title)


def test_rename_validates_title():
    task = make_task()

    with pytest.raises(BusinessRuleViolation):
        task.rename(" ")
    assert task.title == "Revisar documentação"


def test_completing_task_records_completion_time():
    task = make_task()

    task.change_status(TaskStatus.DONE)

    assert task.status == TaskStatus.DONE
    assert task.completed_at is not None


def test_reopening_task_clears_completion_time():
    task = make_task()
    task.change_status(TaskStatus.DONE)

    task.change_status(TaskStatus.IN_PROGRESS)

    assert task.completed_at is None


def test_setting_same_status_keeps_completion_time():
    task = make_task()
    task.change_status(TaskStatus.DONE)
    completed_at = task.completed_at

    task.change_status(TaskStatus.DONE)

    assert task.completed_at == completed_at


def test_creator_and_assignee_can_edit_but_others_cannot():
    creator, assignee, other = uuid4(), uuid4(), uuid4()
    task = make_task(created_by=creator, assigned_to=assignee)

    assert task.can_be_edited_by(creator)
    assert task.can_be_edited_by(assignee)
    assert not task.can_be_edited_by(other)


def test_only_creator_can_delete():
    creator, assignee = uuid4(), uuid4()
    task = make_task(created_by=creator, assigned_to=assignee)

    assert task.can_be_deleted_by(creator)
    assert not task.can_be_deleted_by(assignee)


def test_user_email_is_normalized():
    assert make_user(email="  Ana@Example.COM ").email == "ana@example.com"
    assert normalize_email("X@Y.com") == "x@y.com"


def test_user_rejects_blank_name():
    with pytest.raises(BusinessRuleViolation):
        make_user(name="  ")


def test_deactivate_marks_user_as_inactive_once():
    user = make_user()

    user.deactivate()
    deleted_at = user.deleted_at
    user.deactivate()

    assert not user.is_active
    assert user.deleted_at == deleted_at
