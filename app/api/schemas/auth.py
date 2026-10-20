from pydantic import BaseModel, EmailStr, Field

from app.api.schemas.base import ApiSchema


class LoginRequest(ApiSchema):
    email: EmailStr = Field(examples=["ana@example.com"])
    password: str = Field(min_length=1, max_length=72, examples=["senha-forte-123"])


class TokenResponse(BaseModel):
    """Segue o formato de resposta da RFC 6749 (OAuth 2.0), por isso em snake_case."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Validade do token, em segundos")
