from datetime import timedelta
from uuid import uuid4

import pytest

from app.application.dto import NewTask
from app.application.use_cases.comments import AddComment, DeleteComment, ListComments
from app.domain.entities import Comment, utc_now
from app.domain.exceptions import BusinessRuleViolation, NotFoundError, PermissionDeniedError


@pytest.fixture
def task(make_user, create_task):
    return create_task.execute(make_user(name="Ana"), NewTask(title="Gravar vídeo"))


def test_add_comment_records_author_and_task(uow, make_user, task):
    bruno = make_user(name="Bruno")

    comment = AddComment(uow).execute(bruno, task.id, "  Roteiro pronto  ")

    stored = uow.comments.get(comment.id)
    assert stored.author_id == bruno.id
    assert stored.task_id == task.id
    assert stored.content == "Roteiro pronto"


def test_add_comment_to_unknown_task_raises_not_found(uow, make_user):
    with pytest.raises(NotFoundError, match="Tarefa"):
        AddComment(uow).execute(make_user(), uuid4(), "Olá")


def test_blank_comment_is_rejected(uow, make_user, task):
    with pytest.raises(BusinessRuleViolation):
        AddComment(uow).execute(make_user(name="Bruno"), task.id, "   ")


def test_list_comments_in_chronological_order(uow, make_user, task):
    carla = make_user(name="Carla")
    now = utc_now()
    for offset, content in [(2, "terceiro"), (0, "primeiro"), (1, "segundo")]:
        uow.comments.add(
            Comment(
                task_id=task.id,
                author_id=carla.id,
                content=content,
                created_at=now + timedelta(seconds=offset),
            )
        )

    comments = ListComments(uow).execute(task.id)

    assert [comment.content for comment in comments] == ["primeiro", "segundo", "terceiro"]


def test_list_comments_of_unknown_task_raises_not_found(uow):
    with pytest.raises(NotFoundError):
        ListComments(uow).execute(uuid4())


def test_author_deletes_own_comment(uow, make_user, task):
    bruno = make_user(name="Bruno")
    comment = AddComment(uow).execute(bruno, task.id, "Rascunho")

    DeleteComment(uow).execute(bruno, task.id, comment.id)

    assert uow.comments.get(comment.id) is None


def test_other_user_cannot_delete_comment(uow, make_user, task):
    bruno, carla = make_user(name="Bruno"), make_user(name="Carla")
    comment = AddComment(uow).execute(bruno, task.id, "Rascunho")

    with pytest.raises(PermissionDeniedError):
        DeleteComment(uow).execute(carla, task.id, comment.id)


def test_comment_must_belong_to_the_task_in_the_url(uow, make_user, create_task, task):
    bruno = make_user(name="Bruno")
    other_task = create_task.execute(bruno, NewTask(title="Outra"))
    comment = AddComment(uow).execute(bruno, task.id, "Rascunho")

    with pytest.raises(NotFoundError, match="Comentário"):
        DeleteComment(uow).execute(bruno, other_task.id, comment.id)
