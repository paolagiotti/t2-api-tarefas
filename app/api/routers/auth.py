from fastapi import APIRouter, status

from app.api.dependencies import CurrentPrincipal, LoginDep, LogoutDep
from app.api.schemas.auth import LoginRequest, TokenResponse
from app.api.schemas.errors import error_responses

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/login",
    summary="Autenticar usuário",
    description="Valida e-mail e senha e devolve um token JWT para as demais requisições.",
    responses=error_responses(401, 422),
)
def login(payload: LoginRequest, use_case: LoginDep) -> TokenResponse:
    token = use_case.execute(payload.email, payload.password)
    return TokenResponse(access_token=token.access_token, expires_in=token.expires_in)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Encerrar sessão",
    description="Revoga o token usado na requisição; ele deixa de ser aceito imediatamente.",
    responses=error_responses(401),
)
def logout(principal: CurrentPrincipal, use_case: LogoutDep) -> None:
    use_case.execute(principal)
