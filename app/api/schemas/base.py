from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from pydantic_core import PydanticCustomError


class RequestSchema(BaseModel):
    """Corpo das requisições: JSON em camelCase, no mesmo padrão dos parâmetros do enunciado
    (`assignedTo`, `dueBefore`). Campos desconhecidos são recusados, o que expõe erros de
    digitação do cliente em vez de ignorá-los."""

    model_config = ConfigDict(alias_generator=to_camel, extra="forbid")


class ResponseSchema(BaseModel):
    """Respostas montadas a partir das entidades e serializadas em camelCase."""

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True, from_attributes=True)


def reject_null(value: object) -> object:
    """Para atualizações parciais: o campo pode ser omitido, mas não pode ser enviado como null."""
    if value is None:
        raise PydanticCustomError("null_not_allowed", "não pode ser nulo")
    return value
