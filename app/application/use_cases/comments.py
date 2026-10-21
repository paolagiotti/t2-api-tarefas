import logging
from uuid import UUID

from app.application.ports import UnitOfWork
from app.domain.entities import Comment, User
from app.domain.exceptions import NotFoundError, PermissionDeniedError

logger = logging.getLogger(__name__)


class AddComment:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, actor: User, task_id: UUID, content: str) -> Comment:
        _ensure_task_exists(self._uow, task_id)

        comment = Comment(task_id=task_id, author_id=actor.id, content=content)
        self._uow.comments.add(comment)
        self._uow.commit()
        logger.info("Comentário %s adicionado à tarefa %s por %s", comment.id, task_id, actor.id)
        return comment


class ListComments:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, task_id: UUID) -> list[Comment]:
        _ensure_task_exists(self._uow, task_id)
        return self._uow.comments.list_for_task(task_id)


class DeleteComment:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, actor: User, task_id: UUID, comment_id: UUID) -> None:
        comment = self._uow.comments.get(comment_id)
        if comment is None or comment.task_id != task_id:
            raise NotFoundError("Comentário não encontrado")
        if not comment.can_be_deleted_by(actor.id):
            raise PermissionDeniedError("Apenas o autor pode remover o comentário")

        self._uow.comments.delete(comment)
        self._uow.commit()
        logger.info("Comentário %s removido por %s", comment.id, actor.id)


def _ensure_task_exists(uow: UnitOfWork, task_id: UUID) -> None:
    if uow.tasks.get(task_id) is None:
        raise NotFoundError("Tarefa não encontrada")
