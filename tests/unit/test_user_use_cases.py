from uuid import uuid4

import pytest

from app.application.dto import NewTask, NewUser, UserChanges
from app.application.use_cases.users import CreateUser, DeleteUser, GetUser, UpdateUser
from app.domain.entities import TaskStatus
from app.domain.exceptions import (
    BusinessRuleViolation,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)


def test_create_user_hashes_password_and_normalizes_email(uow, hasher):
    user = CreateUser(uow, hasher).execute(
        NewUser(name="Ana Souza", email="Ana@Example.com", password="senha-segura")
    )

    stored = uow.users.get(user.id)
    assert stored.email == "ana@example.com"
    assert stored.password_hash == hasher.hash("senha-segura")
    assert uow.commits == 1


def test_create_user_rejects_duplicate_email(uow, hasher, make_user):
    make_user(name="Ana")

    with pytest.raises(ConflictError):
        CreateUser(uow, hasher).execute(
            NewUser(name="Outra Ana", email="ANA@example.com", password="senha-segura")
        )


@pytest.mark.parametrize("password", ["curta", "x" * 129])
def test_create_user_rejects_invalid_password(uow, hasher, password):
    with pytest.raises(BusinessRuleViolation):
        CreateUser(uow, hasher).execute(
            NewUser(name="Ana", email="ana@example.com", password=password)
        )
    assert uow.commits == 0


def test_get_user_returns_active_user(uow, make_user):
    user = make_user()

    assert GetUser(uow).execute(user.id).id == user.id


def test_get_user_hides_deactivated_user(uow, make_user):
    user = make_user()
    DeleteUser(uow).execute(user, user.id)

    with pytest.raises(NotFoundError):
        GetUser(uow).execute(user.id)


def test_get_user_raises_not_found_for_unknown_id(uow):
    with pytest.raises(NotFoundError):
        GetUser(uow).execute(uuid4())


def test_update_user_changes_name_email_and_password(uow, hasher, make_user):
    user = make_user()

    updated = UpdateUser(uow, hasher).execute(
        user,
        user.id,
        UserChanges(
            name="Ana Lima",
            email="ana.lima@example.com",
            password="nova-senha-1",
            current_password="senha-segura",
        ),
    )

    stored = uow.users.get(user.id)
    assert updated.name == stored.name == "Ana Lima"
    assert stored.email == "ana.lima@example.com"
    assert hasher.verify("nova-senha-1", stored.password_hash)
    assert stored.updated_at >= user.updated_at


def test_update_user_keeps_fields_not_informed(uow, hasher, make_user):
    user = make_user()

    UpdateUser(uow, hasher).execute(user, user.id, UserChanges(name="Ana Lima"))

    stored = uow.users.get(user.id)
    assert stored.email == user.email
    assert stored.password_hash == user.password_hash


def test_update_user_rejects_email_already_in_use(uow, hasher, make_user):
    ana = make_user(name="Ana")
    make_user(name="Bruno")

    with pytest.raises(ConflictError):
        UpdateUser(uow, hasher).execute(
            ana, ana.id, UserChanges(email="bruno@example.com", current_password="senha-segura")
        )


def test_update_user_accepts_own_email_with_different_case(uow, hasher, make_user):
    ana = make_user(name="Ana")

    updated = UpdateUser(uow, hasher).execute(ana, ana.id, UserChanges(email="ANA@example.com"))

    assert updated.email == "ana@example.com"


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        (UserChanges(password="nova-senha-1"), BusinessRuleViolation),
        (UserChanges(email="novo@example.com"), BusinessRuleViolation),
        (UserChanges(password="nova-senha-1", current_password="errada"), PermissionDeniedError),
    ],
    ids=["senha-sem-confirmacao", "email-sem-confirmacao", "confirmacao-errada"],
)
def test_changing_credentials_requires_current_password(uow, hasher, make_user, changes, error):
    user = make_user()

    with pytest.raises(error):
        UpdateUser(uow, hasher).execute(user, user.id, changes)
    assert uow.commits == 0


def test_update_without_effective_changes_does_not_commit(uow, hasher, make_user):
    user = make_user(name="Ana")

    UpdateUser(uow, hasher).execute(user, user.id, UserChanges(name="Ana"))

    assert uow.commits == 0
    assert uow.users.get(user.id).updated_at == user.updated_at


def test_user_cannot_update_someone_else(uow, hasher, make_user):
    ana, bruno = make_user(name="Ana"), make_user(name="Bruno")

    with pytest.raises(PermissionDeniedError):
        UpdateUser(uow, hasher).execute(ana, bruno.id, UserChanges(name="Invasor"))


def test_delete_user_is_a_soft_delete(uow, make_user):
    user = make_user()

    DeleteUser(uow).execute(user, user.id)

    stored = uow.users.get(user.id)
    assert stored is not None
    assert stored.deleted_at is not None
    assert not stored.is_active


def test_deleting_user_releases_open_tasks_but_keeps_history(uow, make_user, create_task):
    ana, bruno = make_user(name="Ana"), make_user(name="Bruno")
    open_task = create_task.execute(ana, NewTask(title="Em aberto", assigned_to=bruno.id))
    done_task = create_task.execute(ana, NewTask(title="Concluída", assigned_to=bruno.id))
    stored_done = uow.tasks.get(done_task.id)
    stored_done.change_status(TaskStatus.DONE)
    uow.tasks.save(stored_done)

    DeleteUser(uow).execute(bruno, bruno.id)

    assert uow.tasks.get(open_task.id).assigned_to is None
    assert uow.tasks.get(done_task.id).assigned_to == bruno.id


def test_user_cannot_delete_someone_else(uow, make_user):
    ana, bruno = make_user(name="Ana"), make_user(name="Bruno")

    with pytest.raises(PermissionDeniedError):
        DeleteUser(uow).execute(ana, bruno.id)
    assert uow.users.get(bruno.id).is_active
