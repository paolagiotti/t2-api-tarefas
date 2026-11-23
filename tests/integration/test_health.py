import logging

import pytest
from fastapi.testclient import TestClient


def test_health_check_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_response_echoes_valid_request_id(client):
    response = client.get("/health", headers={"X-Request-ID": "abc-123"})

    assert response.headers["X-Request-ID"] == "abc-123"


def test_invalid_request_id_is_replaced(client):
    response = client.get("/health", headers={"X-Request-ID": "<script>"})

    assert response.headers["X-Request-ID"] != "<script>"
    assert len(response.headers["X-Request-ID"]) == 12


def test_unexpected_errors_return_generic_500_and_are_logged(app, caplog):
    def explode() -> None:
        raise RuntimeError("falha inesperada")

    app.add_api_route("/explode", explode)

    with TestClient(app) as client, caplog.at_level(logging.ERROR, logger="app.http"):
        response = client.get("/explode", headers={"X-Request-ID": "req-500"})

    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno do servidor"}
    assert response.headers["X-Request-ID"] == "req-500"
    [record] = [record for record in caplog.records if record.levelno == logging.ERROR]
    assert record.exc_info is not None
    assert "falha inesperada" in caplog.text


def test_unknown_route_returns_404_in_portuguese(client):
    response = client.get("/nao-existe")

    assert response.status_code == 404
    assert response.json() == {"detail": "Rota não encontrada"}


@pytest.mark.parametrize(
    "path",
    ["/users", "/users/{user_id}", "/tasks", "/tasks/{task_id}", "/auth/login", "/auth/logout"],
)
def test_openapi_documents_required_endpoints(client, path):
    spec = client.get("/openapi.json").json()

    assert path in spec["paths"]
    assert "HTTPBearer" in spec["components"]["securitySchemes"]
