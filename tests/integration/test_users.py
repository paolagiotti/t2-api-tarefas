"""Teste de integracao: sobe a API inteira e bate no endpoint via HTTP."""


def payload(**over):
    base = {"name": "Paola", "email": "paola@exemplo.com", "password": "senhaforte123"}
    base.update(over)
    return base


def test_cria_usuario(client):
    r = client.post("/users", json=payload())
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "paola@exemplo.com"
    assert "password" not in body and "password_hash" not in body


def test_email_duplicado_retorna_409(client):
    client.post("/users", json=payload())
    r = client.post("/users", json=payload(name="Outra"))
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


def test_busca_usuario_inexistente_retorna_404(client):
    r = client.get("/users/11111111-1111-1111-1111-111111111111")
    assert r.status_code == 404


def test_soft_delete_esconde_usuario(client):
    user_id = client.post("/users", json=payload()).json()["id"]
    assert client.delete(f"/users/{user_id}").status_code == 204
    assert client.get(f"/users/{user_id}").status_code == 404


def test_validacao_de_senha_curta(client):
    r = client.post("/users", json=payload(password="123"))
    assert r.status_code == 422
