from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.api.schemas.base import RequestSchema, ResponseSchema
from app.domain.entities import COMMENT_MAX_LENGTH


class CommentCreateRequest(RequestSchema):
    content: str = Field(
        min_length=1, max_length=COMMENT_MAX_LENGTH, examples=["Subi a primeira versão dos slides."]
    )


class CommentResponse(ResponseSchema):
    id: UUID
    task_id: UUID
    author_id: UUID
    content: str
    created_at: datetime
