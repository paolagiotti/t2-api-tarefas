"""Hash de senha e JWT. Dono: Pessoa A.

O CONTRATO que a Pessoa B consome esta no fim do arquivo: get_current_user
e require_role. Enquanto a Pessoa A nao terminar, a B usa o stub de teste.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.db.session import get_db
from app.modules.users.models import User, UserRole

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def hash_password(plain: str) -> str:
    # bcrypt trabalha com bytes e limita a senha a 72 bytes.
    return bcrypt.hashpw(plain.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode()[:72], hashed.encode())


def create_access_token(user_id: uuid.UUID, role: UserRole) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role.value,
        "exp": expire,
        "jti": str(uuid.uuid4()),  # id do token, usado no logout (blacklist)
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ---------------------------------------------------------------------------
# CONTRATO consumido pelo modulo de tarefas (Pessoa B)
# ---------------------------------------------------------------------------
def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if not token:
        raise AuthenticationError("Token ausente.")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise AuthenticationError("Token invalido ou expirado.")

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise AuthenticationError("Usuario inexistente ou inativo.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed: UserRole):
    """Uso: dependencies=[Depends(require_role(UserRole.ADMIN))]"""

    def checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise PermissionDeniedError("Voce nao tem permissao para esta operacao.")
        return user

    return checker
