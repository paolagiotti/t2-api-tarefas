from tests.conftest import PASSWORD


def test_login_returns_bearer_token(client, register):
    ana = register("Ana")

    response = client.post("/auth/login", json={"email": ana.email, "password": PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600
    assert body["access_token"].count(".") == 2


def test_login_with_wrong_password_returns_401(client, register):
    ana = register("Ana")

    response = client.post("/auth/login", json={"email": ana.email, "password": "senha-errada"})

    assert response.status_code == 401
    assert response.json() == {"detail": "E-mail ou senha inválidos"}


def test_protected_route_rejects_non_bearer_authorization(client, register):
    ana = register("Ana")

    response = client.get(f"/users/{ana.id}", headers={"Authorization": "Basic YW5hOnNlbmhh"})

    assert response.status_code == 401


def test_protected_route_rejects_invalid_token(client, register):
    ana = register("Ana")

    response = client.get(f"/users/{ana.id}", headers={"Authorization": "Bearer abc.def.ghi"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Token inválido"}


def test_logout_revokes_only_the_current_token(client, register):
    ana = register("Ana")

    logout = client.post("/auth/logout", headers=ana.headers)
    after_logout = client.get(f"/users/{ana.id}", headers=ana.headers)
    new_login = client.post("/auth/login", json={"email": ana.email, "password": PASSWORD})
    new_headers = {"Authorization": f"Bearer {new_login.json()['access_token']}"}

    assert logout.status_code == 204
    assert after_logout.status_code == 401
    assert after_logout.json()["detail"].startswith("Sessão encerrada")
    assert client.get(f"/users/{ana.id}", headers=new_headers).status_code == 200


def test_logout_requires_authentication(client):
    assert client.post("/auth/logout").status_code == 401
