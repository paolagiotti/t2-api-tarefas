from uuid import uuid4

from tests.conftest import PASSWORD


def test_create_user_returns_201_without_sensitive_data(client):
    response = client.post(
        "/users", json={"name": "Ana Souza", "email": "Ana@Example.com", "password": PASSWORD}
    )

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "name", "email", "createdAt", "updatedAt"}
    assert body["email"] == "ana@example.com"
    assert response.headers["Location"].endswith(f"/users/{body['id']}")


def test_create_user_with_existing_email_returns_409(client, register):
    register("Ana")

    response = client.post(
        "/users", json={"name": "Outra", "email": "ana@example.com", "password": PASSWORD}
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Já existe um usuário cadastrado com este e-mail"}


def test_create_user_validates_payload(client):
    response = client.post("/users", json={"name": "", "email": "invalido", "password": "123"})

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Dados inválidos"
    assert {error["field"] for error in body["errors"]} == {
        "body.name",
        "body.email",
        "body.password",
    }


def test_request_body_must_follow_the_documented_contract(client, register):
    ana = register("Ana")
    url = f"/users/{ana.id}"

    unknown = client.put(url, json={"full_name": "Ana Lima"}, headers=ana.headers)
    null = client.put(url, json={"name": None}, headers=ana.headers)
    broken = client.put(
        url, content="{nome:", headers={**ana.headers, "Content-Type": "application/json"}
    )

    assert unknown.json()["errors"] == [
        {"field": "body.full_name", "message": "campo não reconhecido"}
    ]
    assert null.json()["errors"] == [{"field": "body.name", "message": "não pode ser nulo"}]
    assert broken.json()["errors"] == [{"field": "body", "message": "JSON inválido"}]


def test_get_user_requires_authentication(client, register):
    ana = register("Ana")

    response = client.get(f"/users/{ana.id}")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_get_user_returns_profile(client, register):
    ana, bruno = register("Ana"), register("Bruno")

    response = client.get(f"/users/{bruno.id}", headers=ana.headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Bruno"


def test_get_unknown_user_returns_404(client, register):
    ana = register("Ana")

    response = client.get(f"/users/{uuid4()}", headers=ana.headers)

    assert response.status_code == 404


def test_get_user_with_malformed_id_returns_422(client, register):
    ana = register("Ana")

    response = client.get("/users/123", headers=ana.headers)

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "path.user_id"


def test_user_updates_own_profile(client, register):
    ana = register("Ana")

    response = client.put(f"/users/{ana.id}", json={"name": "Ana Lima"}, headers=ana.headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Ana Lima"
    assert response.json()["email"] == ana.email


def test_user_cannot_update_another_user(client, register):
    ana, bruno = register("Ana"), register("Bruno")

    response = client.put(f"/users/{bruno.id}", json={"name": "Invasor"}, headers=ana.headers)

    assert response.status_code == 403


def test_password_change_takes_effect_on_next_login(client, register):
    ana = register("Ana")

    client.put(
        f"/users/{ana.id}",
        json={"password": "nova-senha-456", "currentPassword": PASSWORD},
        headers=ana.headers,
    )

    old = client.post("/auth/login", json={"email": ana.email, "password": PASSWORD})
    new = client.post("/auth/login", json={"email": ana.email, "password": "nova-senha-456"})
    assert old.status_code == 401
    assert new.status_code == 200


def test_changing_email_requires_the_current_password(client, register):
    ana = register("Ana")
    url = f"/users/{ana.id}"

    missing = client.put(url, json={"email": "nova@example.com"}, headers=ana.headers)
    wrong = client.put(
        url, json={"email": "nova@example.com", "currentPassword": "errada"}, headers=ana.headers
    )
    right = client.put(
        url, json={"email": "nova@example.com", "currentPassword": PASSWORD}, headers=ana.headers
    )

    assert missing.status_code == 422
    assert wrong.status_code == 403
    assert right.status_code == 200
    assert right.json()["email"] == "nova@example.com"


def test_update_without_changes_keeps_updated_at(client, register):
    ana = register("Ana")
    before = client.get(f"/users/{ana.id}", headers=ana.headers).json()

    response = client.put(f"/users/{ana.id}", json={"name": "Ana"}, headers=ana.headers)

    assert response.status_code == 200
    assert response.json()["updatedAt"] == before["updatedAt"]


def test_deleting_user_unassigns_their_open_tasks(client, register):
    ana, bruno = register("Ana"), register("Bruno")
    task = client.post(
        "/tasks", json={"title": "Revisar", "assignedTo": bruno.id}, headers=ana.headers
    ).json()

    client.delete(f"/users/{bruno.id}", headers=bruno.headers)

    assert client.get(f"/tasks/{task['id']}", headers=ana.headers).json()["assignedTo"] is None


def test_tasks_of_a_removed_creator_can_be_deleted_by_the_team(client, register):
    ana, bruno = register("Ana"), register("Bruno")
    task = client.post(
        "/tasks", json={"title": "Da Ana", "assignedTo": ana.id}, headers=ana.headers
    ).json()

    client.delete(f"/users/{ana.id}", headers=ana.headers)

    assert client.delete(f"/tasks/{task['id']}", headers=bruno.headers).status_code == 204


def test_delete_user_is_soft_delete(client, register):
    ana, bruno = register("Ana"), register("Bruno")

    response = client.delete(f"/users/{ana.id}", headers=ana.headers)

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/users/{ana.id}", headers=bruno.headers).status_code == 404
    assert client.get(f"/users/{bruno.id}", headers=ana.headers).status_code == 401
    login = client.post("/auth/login", json={"email": ana.email, "password": PASSWORD})
    assert login.status_code == 401


def test_user_cannot_delete_another_user(client, register):
    ana, bruno = register("Ana"), register("Bruno")

    response = client.delete(f"/users/{bruno.id}", headers=ana.headers)

    assert response.status_code == 403
