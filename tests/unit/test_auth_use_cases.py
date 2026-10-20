from datetime import timedelta

import pytest

from app.application.use_cases.auth import AuthenticateToken, Login, Logout
from app.application.use_cases.users import DeleteUser
from app.domain.entities import utc_now
from app.domain.exceptions import AuthenticationError


def test_login_returns_token_for_valid_credentials(uow, hasher, tokens, make_user):
    user = make_user(password="senha-segura")

    issued = Login(uow, hasher, tokens).execute("ana@example.com", "senha-segura")

    assert tokens.decode(issued.access_token).user_id == user.id
    assert issued.expires_in == 3600


def test_login_ignores_email_case(uow, hasher, tokens, make_user):
    make_user(password="senha-segura")

    issued = Login(uow, hasher, tokens).execute("  ANA@example.com ", "senha-segura")

    assert issued.access_token


@pytest.mark.parametrize(
    ("email", "password"),
    [("ana@example.com", "senha-errada"), ("ninguem@example.com", "senha-segura")],
)
def test_login_rejects_invalid_credentials(uow, hasher, tokens, make_user, email, password):
    make_user(password="senha-segura")

    with pytest.raises(AuthenticationError, match="E-mail ou senha inválidos"):
        Login(uow, hasher, tokens).execute(email, password)


def test_login_rejects_deactivated_user(uow, hasher, tokens, make_user):
    user = make_user(password="senha-segura")
    DeleteUser(uow).execute(user, user.id)

    with pytest.raises(AuthenticationError):
        Login(uow, hasher, tokens).execute("ana@example.com", "senha-segura")


def test_authenticate_returns_user_and_claims(uow, tokens, make_user):
    user = make_user()
    issued = tokens.issue(user.id)

    principal = AuthenticateToken(uow, tokens).execute(issued.access_token)

    assert principal.user.id == user.id
    assert principal.claims.token_id == issued.token_id


def test_authenticate_rejects_unknown_token(uow, tokens):
    with pytest.raises(AuthenticationError):
        AuthenticateToken(uow, tokens).execute("token-inexistente")


def test_authenticate_rejects_token_of_deactivated_user(uow, tokens, make_user):
    user = make_user()
    issued = tokens.issue(user.id)
    DeleteUser(uow).execute(user, user.id)

    with pytest.raises(AuthenticationError):
        AuthenticateToken(uow, tokens).execute(issued.access_token)


def test_logout_revokes_current_token(uow, tokens, make_user):
    user = make_user()
    issued = tokens.issue(user.id)
    authenticate = AuthenticateToken(uow, tokens)

    Logout(uow).execute(authenticate.execute(issued.access_token))

    with pytest.raises(AuthenticationError, match="Sessão encerrada"):
        authenticate.execute(issued.access_token)
    assert uow.commits == 1


def test_logout_purges_expired_revocations(uow, tokens, make_user):
    user = make_user()
    uow.revoked_tokens.add("token-antigo", utc_now() - timedelta(minutes=1))
    principal = AuthenticateToken(uow, tokens).execute(tokens.issue(user.id).access_token)

    Logout(uow).execute(principal)

    assert not uow.revoked_tokens.contains("token-antigo")
    assert uow.revoked_tokens.contains(principal.claims.token_id)
