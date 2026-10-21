from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.ports import CommentRepository
from app.domain.entities import Comment
from app.infrastructure.models import CommentModel


class SqlAlchemyCommentRepository(CommentRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, comment: Comment) -> None:
        self._session.add(
            CommentModel(
                id=comment.id,
                task_id=comment.task_id,
                author_id=comment.author_id,
                content=comment.content,
                created_at=comment.created_at,
            )
        )

    def get(self, comment_id: UUID) -> Comment | None:
        model = self._session.get(CommentModel, comment_id)
        return _to_entity(model) if model else None

    def list_for_task(self, task_id: UUID) -> list[Comment]:
        query = (
            select(CommentModel)
            .where(CommentModel.task_id == task_id)
            .order_by(CommentModel.created_at, CommentModel.id)
        )
        return [_to_entity(model) for model in self._session.scalars(query)]

    def delete(self, comment: Comment) -> None:
        self._session.delete(self._session.get_one(CommentModel, comment.id))


def _to_entity(model: CommentModel) -> Comment:
    return Comment(
        id=model.id,
        task_id=model.task_id,
        author_id=model.author_id,
        content=model.content,
        created_at=model.created_at,
    )
