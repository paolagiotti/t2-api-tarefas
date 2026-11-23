from datetime import timedelta
from uuid import uuid4

import jwt
import pytest

from app.domain.exceptions import AuthenticationError, BusinessRuleViolation
from app.infrastructure.security import BcryptPasswordHasher, JwtTokenService

SECRET = "segredo-de-teste-com-pelo-menos-32-caracteres"
ISSUER = "t2-api-tarefas"


@pytest.fixture
def hasher() -> BcryptPasswordHasher:
    return BcryptPasswordHasher(rounds=4)


def test_bcrypt_verifies_only_the_original_password(hasher):
    password_hash = hasher.hash("senha-segura")

    assert password_hash.startswith("$2b$04$")
    assert hasher.verify("senha-segura", password_hash)
    assert not hasher.verify("senha-errada", password_hash)


def test_bcrypt_uses_random_salt(hasher):
    assert hasher.hash("senha-segura") != hasher.hash("senha-segura")


def test_bcrypt_treats_malformed_input_as_wrong_password(hasher):
    assert not hasher.verify("senha-segura", "nao-e-um-hash")
    assert not hasher.verify("x" * 100, hasher.hash("senha-segura"))


def test_bcrypt_refuses_passwords_longer_than_72_bytes(hasher):
    with pytest.raises(BusinessRuleViolation):
        hasher.hash("ç" * 37)


def test_jwt_round_trip():
    service = JwtTokenService(SECRET)
    user_id = uuid4()

    issued = service.issue(user_id)
    claims = service.decode(issued.access_token)

    assert claims.user_id == user_id
    assert claims.token_id == issued.token_id
    assert claims.expires_at == issued.expires_at.replace(microsecond=0)
    assert issued.expires_in == 3600


def test_jwt_rejects_expired_token():
    service = JwtTokenService(SECRET, expires_in=timedelta(seconds=-1))

    with pytest.raises(AuthenticationError, match="expirado"):
        service.decode(service.issue(uuid4()).access_token)


def test_jwt_rejects_token_signed_with_another_secret():
    other = JwtTokenService("outro-segredo-com-pelo-menos-32-caracteres")

    with pytest.raises(AuthenticationError, match="inválido"):
        JwtTokenService(SECRET).decode(other.issue(uuid4()).access_token)


@pytest.mark.parametrize(
    "payload",
    [
        {"sub": "nao-e-uuid", "jti": "abc", "iat": 1, "exp": 4_102_444_800, "iss": ISSUER},
        {"sub": str(uuid4()), "iat": 1, "exp": 4_102_444_800, "iss": ISSUER},
        {"sub": str(uuid4()), "jti": "abc", "iat": 1, "exp": 4_102_444_800, "iss": "outro"},
    ],
    ids=["sub-invalido", "sem-jti", "emissor-errado"],
)
def test_jwt_rejects_malformed_claims(payload):
    token = jwt.encode(payload, SECRET, algorithm="HS256")

    with pytest.raises(AuthenticationError, match="inválido"):
        JwtTokenService(SECRET).decode(token)


def test_jwt_rejects_garbage():
    with pytest.raises(AuthenticationError):
        JwtTokenService(SECRET).decode("isto.nao.e-um-jwt")
