import logging

from app.application.dto import IssuedToken, Principal
from app.application.ports import PasswordHasher, TokenService, UnitOfWork
from app.domain.entities import normalize_email, utc_now
from app.domain.exceptions import AuthenticationError

logger = logging.getLogger(__name__)


class Login:
    def __init__(self, uow: UnitOfWork, hasher: PasswordHasher, tokens: TokenService) -> None:
        self._uow = uow
        self._hasher = hasher
        self._tokens = tokens

    def execute(self, email: str, password: str) -> IssuedToken:
        user = self._uow.users.get_by_email(normalize_email(email))
        valid = (
            user is not None
            and user.is_active
            and self._hasher.verify(password, user.password_hash)
        )
        if not valid:
            logger.warning("Tentativa de login recusada")
            raise AuthenticationError("E-mail ou senha inválidos")

        token = self._tokens.issue(user.id)
        logger.info("Usuário %s autenticado", user.id)
        return token


class AuthenticateToken:
    """Valida o token recebido e identifica o usuário autenticado."""

    def __init__(self, uow: UnitOfWork, tokens: TokenService) -> None:
        self._uow = uow
        self._tokens = tokens

    def execute(self, token: str) -> Principal:
        claims = self._tokens.decode(token)
        if self._uow.revoked_tokens.contains(claims.token_id):
            raise AuthenticationError("Sessão encerrada. Faça login novamente")

        user = self._uow.users.get(claims.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Usuário do token não está mais ativo")
        return Principal(user=user, claims=claims)


class Logout:
    """Revoga o token atual até a sua expiração.

    JWT não guarda estado no servidor, então o logout registra o identificador do token (jti)
    em uma lista de revogados, consultada a cada requisição.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, principal: Principal) -> None:
        self._uow.revoked_tokens.add(principal.claims.token_id, principal.claims.expires_at)
        self._uow.revoked_tokens.remove_expired(utc_now())
        self._uow.commit()
        logger.info("Usuário %s encerrou a sessão", principal.user.id)
