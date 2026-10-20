from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.api.schemas.base import ApiSchema
from app.application.dto import NewUser, UserChanges


class UserCreateRequest(ApiSchema):
    name: str = Field(min_length=1, max_length=120, examples=["Ana Souza"])
    email: EmailStr = Field(examples=["ana@example.com"])
    password: str = Field(min_length=8, max_length=72, examples=["senha-forte-123"])

    def to_input(self) -> NewUser:
        return NewUser(name=self.name, email=self.email, password=self.password)


class UserUpdateRequest(ApiSchema):
    """Somente os campos enviados são alterados."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)

    def to_input(self) -> UserChanges:
        return UserChanges(name=self.name, email=self.email, password=self.password)


class UserResponse(ApiSchema):
    id: UUID
    name: str
    email: str
    created_at: datetime
    updated_at: datetime
