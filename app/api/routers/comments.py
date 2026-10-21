from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.api.dependencies import (
    AddCommentDep,
    CurrentUser,
    DeleteCommentDep,
    ListCommentsDep,
    get_current_user,
)
from app.api.schemas.comments import CommentCreateRequest, CommentResponse
from app.api.schemas.errors import error_responses

router = APIRouter(
    prefix="/tasks/{task_id}/comments",
    tags=["Comentários"],
    dependencies=[Depends(get_current_user)],
    responses=error_responses(401, 404, 422),
)


@router.post("", status_code=status.HTTP_201_CREATED, summary="Comentar em uma tarefa")
def add_comment(
    task_id: UUID, payload: CommentCreateRequest, actor: CurrentUser, use_case: AddCommentDep
) -> CommentResponse:
    return CommentResponse.model_validate(use_case.execute(actor, task_id, payload.content))


@router.get("", summary="Listar comentários da tarefa", description="Em ordem cronológica.")
def list_comments(task_id: UUID, use_case: ListCommentsDep) -> list[CommentResponse]:
    return [CommentResponse.model_validate(comment) for comment in use_case.execute(task_id)]


@router.delete(
    "/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover comentário",
    description="Somente o autor pode remover o próprio comentário.",
    responses=error_responses(403),
)
def delete_comment(
    task_id: UUID, comment_id: UUID, actor: CurrentUser, use_case: DeleteCommentDep
) -> None:
    use_case.execute(actor, task_id, comment_id)
