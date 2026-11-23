from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.api.schemas.base import ApiSchema
from app.application.dto import NewUser, UserChanges
from app.application.use_cases.users import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from app.domain.entities import USER_NAME_MAX_LENGTH


class UserCreateRequest(ApiSchema):
    name: str = Field(min_length=1, max_length=USER_NAME_MAX_LENGTH, examples=["Ana Souza"])
    email: EmailStr = Field(examples=["ana@example.com"])
    password: str = Field(
        min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH, examples=["senha-forte-123"]
    )

    def to_input(self) -> NewUser:
        return NewUser(name=self.name, email=self.email, password=self.password)


class UserUpdateRequest(ApiSchema):
    """Somente os campos enviados são alterados. Para trocar e-mail ou senha, informe também
    `currentPassword`."""

    name: str | None = Field(default=None, min_length=1, max_length=USER_NAME_MAX_LENGTH)
    email: EmailStr | None = None
    password: str | None = Field(
        default=None, min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH
    )
    current_password: str | None = Field(default=None, max_length=PASSWORD_MAX_LENGTH)

    def to_input(self) -> UserChanges:
        return UserChanges(
            name=self.name,
            email=self.email,
            password=self.password,
            current_password=self.current_password,
        )


class UserResponse(ApiSchema):
    id: UUID
    name: str
    email: str
    created_at: datetime
    updated_at: datetime
