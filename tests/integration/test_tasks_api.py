from uuid import uuid4


def create_task(client, owner, **fields):
    payload = {"title": "Preparar apresentação", **fields}
    response = client.post("/tasks", json=payload, headers=owner.headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_tasks_require_authentication(client):
    assert client.get("/tasks").status_code == 401
    assert client.post("/tasks", json={"title": "Sem login"}).status_code == 401


def test_create_task_returns_201_with_defaults(client, register):
    ana = register("Ana")

    task = create_task(client, ana, description="Slides + roteiro", dueDate="2026-11-30")

    assert task["status"] == "pending"
    assert task["priority"] == "medium"
    assert task["dueDate"] == "2026-11-30"
    assert task["createdBy"] == ana.id
    assert task["assignedTo"] is None
    assert task["completedAt"] is None


def test_create_task_validates_payload(client, register):
    ana = register("Ana")

    response = client.post("/tasks", json={"title": "", "priority": "urgente"}, headers=ana.headers)

    assert response.status_code == 422
    assert {error["field"] for error in response.json()["errors"]} == {
        "body.title",
        "body.priority",
    }


def test_title_line_breaks_become_spaces(client, register):
    ana = register("Ana")

    response = client.post("/tasks", json={"title": "Linha 1\nLinha 2"}, headers=ana.headers)

    assert response.status_code == 201
    assert response.json()["title"] == "Linha 1 Linha 2"


def test_create_task_with_unknown_assignee_returns_422(client, register):
    ana = register("Ana")

    response = client.post(
        "/tasks", json={"title": "Revisar", "assignedTo": str(uuid4())}, headers=ana.headers
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "O responsável informado não existe ou foi removido"}


def test_get_task(client, register):
    ana = register("Ana")
    task = create_task(client, ana)

    response = client.get(f"/tasks/{task['id']}", headers=ana.headers)

    assert response.status_code == 200
    assert response.json() == task


def test_get_unknown_task_returns_404(client, register):
    ana = register("Ana")

    response = client.get(f"/tasks/{uuid4()}", headers=ana.headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Tarefa não encontrada"}


def test_list_tasks_assigned_to_a_user(client, register):
    ana, bruno = register("Ana"), register("Bruno")
    create_task(client, ana, title="Da Ana", assignedTo=ana.id)
    create_task(client, ana, title="Do Bruno", assignedTo=bruno.id)
    create_task(client, ana, title="Sem responsável")

    response = client.get("/tasks", params={"assignedTo": bruno.id}, headers=ana.headers)

    assert response.status_code == 200
    assert [task["title"] for task in response.json()] == ["Do Bruno"]


def test_list_tasks_paginates(client, register):
    ana = register("Ana")
    for index in range(3):
        create_task(client, ana, title=f"Tarefa {index}")

    page = client.get("/tasks", params={"limit": 2, "offset": 1}, headers=ana.headers)
    invalid = client.get("/tasks", params={"limit": 0}, headers=ana.headers)

    assert [task["title"] for task in page.json()] == ["Tarefa 1", "Tarefa 0"]
    assert invalid.status_code == 422


def test_assignee_completes_task(client, register):
    ana, bruno = register("Ana"), register("Bruno")
    task = create_task(client, ana, assignedTo=bruno.id)

    response = client.put(f"/tasks/{task['id']}", json={"status": "done"}, headers=bruno.headers)

    assert response.status_code == 200
    assert response.json()["status"] == "done"
    assert response.json()["completedAt"] is not None


def test_partial_update_keeps_other_fields(client, register):
    ana = register("Ana")
    task = create_task(client, ana, description="Detalhes", priority="high")

    response = client.put(
        f"/tasks/{task['id']}", json={"title": "Novo título"}, headers=ana.headers
    )

    body = response.json()
    assert body["title"] == "Novo título"
    assert body["description"] == "Detalhes"
    assert body["priority"] == "high"


def test_update_with_null_clears_optional_fields(client, register):
    ana = register("Ana")
    task = create_task(client, ana, assignedTo=ana.id, dueDate="2026-12-01")

    response = client.put(
        f"/tasks/{task['id']}", json={"assignedTo": None, "dueDate": None}, headers=ana.headers
    )

    assert response.json()["assignedTo"] is None
    assert response.json()["dueDate"] is None


def test_update_rejects_null_title(client, register):
    ana = register("Ana")
    task = create_task(client, ana)

    response = client.put(f"/tasks/{task['id']}", json={"title": None}, headers=ana.headers)

    assert response.status_code == 422


def test_other_user_cannot_update_task(client, register):
    ana, carla = register("Ana"), register("Carla")
    task = create_task(client, ana)

    response = client.put(f"/tasks/{task['id']}", json={"title": "x"}, headers=carla.headers)

    assert response.status_code == 403


def test_creator_deletes_task(client, register):
    ana = register("Ana")
    task = create_task(client, ana)

    response = client.delete(f"/tasks/{task['id']}", headers=ana.headers)

    assert response.status_code == 204
    assert client.get(f"/tasks/{task['id']}", headers=ana.headers).status_code == 404


def test_assignee_cannot_delete_task(client, register):
    ana, bruno = register("Ana"), register("Bruno")
    task = create_task(client, ana, assignedTo=bruno.id)

    response = client.delete(f"/tasks/{task['id']}", headers=bruno.headers)

    assert response.status_code == 403
