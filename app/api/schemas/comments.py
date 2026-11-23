from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.api.schemas.base import ApiSchema
from app.domain.entities import COMMENT_MAX_LENGTH


class CommentCreateRequest(ApiSchema):
    content: str = Field(
        min_length=1, max_length=COMMENT_MAX_LENGTH, examples=["Subi a primeira versão dos slides."]
    )


class CommentResponse(ApiSchema):
    id: UUID
    task_id: UUID
    author_id: UUID
    content: str
    created_at: datetime
