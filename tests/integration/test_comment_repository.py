import pytest

from app.domain.entities import Comment, Task, User
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def uow(session):
    return SqlAlchemyUnitOfWork(session)


@pytest.fixture
def task(uow) -> Task:
    author = User(name="Ana", email="ana@example.com", password_hash="hash")
    uow.users.add(author)
    uow.commit()
    task = Task(title="Gravar vídeo", created_by=author.id)
    uow.tasks.add(task)
    uow.commit()
    return task


def test_comment_round_trip(uow, task):
    comment = Comment(task_id=task.id, author_id=task.created_by, content="Roteiro pronto")

    uow.comments.add(comment)
    uow.commit()

    assert uow.comments.get(comment.id) == comment
    assert uow.comments.list_for_task(task.id) == [comment]


def test_deleting_a_task_removes_its_comments(uow, task):
    comment = Comment(task_id=task.id, author_id=task.created_by, content="Roteiro pronto")
    uow.comments.add(comment)
    uow.commit()

    uow.tasks.delete(task)
    uow.commit()

    assert uow.comments.get(comment.id) is None
    assert uow.comments.list_for_task(task.id) == []
