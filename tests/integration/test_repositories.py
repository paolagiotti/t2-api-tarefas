from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy.exc import StatementError

from app.application.dto import TaskFilters
from app.domain.entities import Task, TaskPriority, TaskStatus, User, utc_now
from app.domain.exceptions import ConflictError


def make_user(**overrides) -> User:
    data = {"name": "Ana", "email": f"{uuid4().hex[:10]}@example.com", "password_hash": "hash"}
    data.update(overrides)
    return User(**data)


def add_users(uow, count: int) -> list[User]:
    users = [make_user(name=f"Pessoa {index}") for index in range(count)]
    for user in users:
        uow.users.add(user)
    uow.commit()
    return users


def test_user_round_trip_preserves_all_fields(uow):
    user = make_user()

    uow.users.add(user)
    uow.commit()

    assert uow.users.get(user.id) == user
    assert uow.users.get_by_email(user.email) == user


def test_unknown_ids_return_none(uow):
    assert uow.users.get(uuid4()) is None
    assert uow.users.get_by_email("ninguem@example.com") is None
    assert uow.tasks.get(uuid4()) is None


def test_save_persists_user_changes(uow):
    [user] = add_users(uow, 1)

    user.rename("Ana Lima")
    user.deactivate()
    uow.users.save(user)
    uow.commit()

    stored = uow.users.get(user.id)
    assert stored.name == "Ana Lima"
    assert stored.deleted_at == user.deleted_at


def test_duplicate_email_is_reported_as_conflict(uow):
    uow.users.add(make_user(email="ana@example.com"))
    uow.users.add(make_user(email="ana@example.com"))

    with pytest.raises(ConflictError):
        uow.commit()


def test_datetimes_are_returned_in_utc(uow):
    local_time = datetime(2026, 10, 18, 9, 30, tzinfo=timezone(timedelta(hours=-3)))
    user = make_user(created_at=local_time, updated_at=local_time)

    uow.users.add(user)
    uow.commit()

    stored = uow.users.get(user.id)
    assert stored.created_at == local_time
    assert stored.created_at.utcoffset() == timedelta(0)


def test_naive_datetimes_are_rejected(uow):
    uow.users.add(make_user(created_at=datetime(2026, 1, 1)))

    with pytest.raises(StatementError):
        uow.commit()


def test_task_round_trip_preserves_all_fields(uow):
    ana, bruno = add_users(uow, 2)
    task = Task(
        title="Gravar demo",
        description="Até 15 minutos",
        priority=TaskPriority.HIGH,
        due_date=date(2026, 11, 20),
        created_by=ana.id,
        assigned_to=bruno.id,
    )
    task.change_status(TaskStatus.DONE)

    uow.tasks.add(task)
    uow.commit()

    assert uow.tasks.get(task.id) == task


def test_save_and_delete_task(uow):
    [ana] = add_users(uow, 1)
    task = Task(title="Rascunho", created_by=ana.id)
    uow.tasks.add(task)
    uow.commit()

    task.rename("Versão final")
    uow.tasks.save(task)
    uow.commit()
    assert uow.tasks.get(task.id).title == "Versão final"

    uow.tasks.delete(task)
    uow.commit()
    assert uow.tasks.get(task.id) is None


def test_find_filters_by_assignee_and_paginates_newest_first(uow):
    ana, bruno = add_users(uow, 2)
    start = utc_now()
    for index in range(5):
        uow.tasks.add(
            Task(
                title=f"T{index}",
                created_by=ana.id,
                assigned_to=bruno.id if index % 2 else None,
                created_at=start + timedelta(seconds=index),
            )
        )
    uow.commit()

    assigned = uow.tasks.find(TaskFilters(assigned_to=bruno.id))
    page = uow.tasks.find(TaskFilters(limit=2, offset=1))

    assert [task.title for task in assigned] == ["T3", "T1"]
    assert [task.title for task in page] == ["T3", "T2"]


def test_revoked_tokens_expire(uow):
    now = utc_now()
    uow.revoked_tokens.add("ativo", now + timedelta(hours=1))
    uow.revoked_tokens.add("vencido", now - timedelta(hours=1))
    uow.commit()

    removed = uow.revoked_tokens.remove_expired(now)
    uow.commit()

    assert removed == 1
    assert uow.revoked_tokens.contains("ativo")
    assert not uow.revoked_tokens.contains("vencido")
