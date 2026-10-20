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
