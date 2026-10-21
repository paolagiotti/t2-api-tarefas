from uuid import uuid4

import pytest


@pytest.fixture
def task(client, register):
    ana = register("Ana")
    response = client.post("/tasks", json={"title": "Gravar vídeo"}, headers=ana.headers)
    return response.json()


def comments_url(task_id: str) -> str:
    return f"/tasks/{task_id}/comments"


def test_comments_require_authentication(client, task):
    assert client.get(comments_url(task["id"])).status_code == 401


def test_add_comment_returns_201(client, register, task):
    bruno = register("Bruno")

    response = client.post(
        comments_url(task["id"]), json={"content": "Roteiro pronto"}, headers=bruno.headers
    )

    assert response.status_code == 201
    body = response.json()
    assert body["taskId"] == task["id"]
    assert body["authorId"] == bruno.id
    assert body["content"] == "Roteiro pronto"
    assert body["createdAt"]


def test_list_comments_in_creation_order(client, register, task):
    bruno = register("Bruno")
    for content in ("primeiro", "segundo"):
        client.post(comments_url(task["id"]), json={"content": content}, headers=bruno.headers)

    response = client.get(comments_url(task["id"]), headers=bruno.headers)

    assert response.status_code == 200
    assert [comment["content"] for comment in response.json()] == ["primeiro", "segundo"]


def test_comment_on_unknown_task_returns_404(client, register):
    bruno = register("Bruno")

    response = client.post(
        comments_url(str(uuid4())), json={"content": "Oi"}, headers=bruno.headers
    )

    assert response.status_code == 404


def test_empty_comment_returns_422(client, register, task):
    bruno = register("Bruno")

    response = client.post(comments_url(task["id"]), json={"content": ""}, headers=bruno.headers)

    assert response.status_code == 422


def test_only_author_deletes_comment(client, register, task):
    bruno, carla = register("Bruno"), register("Carla")
    created = client.post(
        comments_url(task["id"]), json={"content": "Rascunho"}, headers=bruno.headers
    ).json()
    url = f"{comments_url(task['id'])}/{created['id']}"

    forbidden = client.delete(url, headers=carla.headers)
    deleted = client.delete(url, headers=bruno.headers)

    assert forbidden.status_code == 403
    assert deleted.status_code == 204
    assert client.get(comments_url(task["id"]), headers=bruno.headers).json() == []
