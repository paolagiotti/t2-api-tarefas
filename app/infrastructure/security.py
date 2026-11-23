from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import bcrypt
import jwt

from app.application.dto import IssuedToken, TokenClaims
from app.application.ports import PasswordHasher, TokenService
from app.domain.entities import utc_now
from app.domain.exceptions import AuthenticationError, BusinessRuleViolation

BCRYPT_MAX_BYTES = 72


class BcryptPasswordHasher(PasswordHasher):
    def __init__(self, rounds: int = 12) -> None:
        self._rounds = rounds

    def hash(self, password: str) -> str:
        encoded = password.encode()
        if len(encoded) > BCRYPT_MAX_BYTES:
            # O bcrypt só considera os primeiros 72 bytes; recusar é mais seguro que truncar.
            raise BusinessRuleViolation(f"A senha deve ter no máximo {BCRYPT_MAX_BYTES} bytes")
        return bcrypt.hashpw(encoded, bcrypt.gensalt(self._rounds)).decode()

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except ValueError:
            # Hash malformado ou senha acima do limite do bcrypt: tratamos como senha incorreta.
            return False


class JwtTokenService(TokenService):
    def __init__(
        self,
        secret: str,
        *,
        algorithm: str = "HS256",
        expires_in: timedelta = timedelta(hours=1),
        issuer: str = "t2-api-tarefas",
    ) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._expires_in = expires_in
        self._issuer = issuer

    def issue(self, user_id: UUID) -> IssuedToken:
        issued_at = utc_now()
        expires_at = issued_at + self._expires_in
        token_id = uuid4().hex
        payload = {
            "sub": str(user_id),
            "jti": token_id,
            "iat": issued_at,
            "exp": expires_at,
            "iss": self._issuer,
        }
        return IssuedToken(
            access_token=jwt.encode(payload, self._secret, algorithm=self._algorithm),
            expires_in=int(self._expires_in.total_seconds()),
        )

    def decode(self, token: str) -> TokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                options={"require": ["sub", "jti", "iat", "exp"]},
            )
            user_id = UUID(payload["sub"])
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Token expirado. Faça login novamente") from exc
        except (jwt.InvalidTokenError, ValueError) as exc:
            raise AuthenticationError("Token inválido") from exc

        return TokenClaims(
            user_id=user_id,
            token_id=payload["jti"],
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )
