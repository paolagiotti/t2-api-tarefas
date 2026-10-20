from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiSchema(BaseModel):
    """Base dos contratos HTTP: JSON em camelCase, no mesmo padrão dos parâmetros do enunciado
    (`assignedTo`, `dueBefore`)."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        from_attributes=True,
    )
