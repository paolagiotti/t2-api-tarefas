from typing import Any

from pydantic import BaseModel, Field


class FieldError(BaseModel):
    field: str = Field(examples=["body.title"])
    message: str = Field(examples=["String should have at least 1 character"])


class ErrorResponse(BaseModel):
    detail: str = Field(examples=["Tarefa não encontrada"])
    errors: list[FieldError] | None = Field(
        default=None, description="Presente apenas em erros de validação dos dados enviados"
    )


_DESCRIPTIONS = {
    401: "Token ausente, inválido, expirado ou revogado",
    403: "O usuário autenticado não tem permissão para a operação",
    404: "Recurso não encontrado",
    409: "Conflito com dados já existentes",
    422: "Dados inválidos ou regra de negócio violada",
}


def error_responses(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """Documenta no OpenAPI as respostas de erro de um endpoint."""
    return {
        code: {"model": ErrorResponse, "description": _DESCRIPTIONS[code]} for code in status_codes
    }
