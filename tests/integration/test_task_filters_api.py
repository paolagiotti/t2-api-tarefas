import pytest


@pytest.fixture
def seeded(client, register):
    """Cria um conjunto pequeno e variado de tarefas para exercitar os filtros."""
    ana, bruno = register("Ana"), register("Bruno")
    tasks = [
        {"title": "Relatório", "priority": "high", "dueDate": "2026-11-10", "assignedTo": ana.id},
        {"title": "Slides", "priority": "high", "dueDate": "2026-12-15", "assignedTo": bruno.id},
        {"title": "Vídeo", "priority": "low", "dueDate": "2026-11-20", "assignedTo": bruno.id},
        {"title": "Revisão", "priority": "medium"},
    ]
    ids = {}
    for payload in tasks:
        response = client.post("/tasks", json=payload, headers=ana.headers)
        assert response.status_code == 201, response.text
        ids[payload["title"]] = response.json()["id"]
    client.put(f"/tasks/{ids['Relatório']}", json={"status": "done"}, headers=ana.headers)
    client.put(f"/tasks/{ids['Vídeo']}", json={"status": "in_progress"}, headers=bruno.headers)
    return ana, bruno


def titles(client, headers, **params):
    response = client.get("/tasks", params=params, headers=headers)
    assert response.status_code == 200, response.text
    return sorted(task["title"] for task in response.json())


def test_filter_by_status(client, seeded):
    ana, _ = seeded

    assert titles(client, ana.headers, status="done") == ["Relatório"]
    assert titles(client, ana.headers, status="pending") == ["Revisão", "Slides"]


def test_filter_by_priority(client, seeded):
    ana, _ = seeded

    assert titles(client, ana.headers, priority="high") == ["Relatório", "Slides"]


def test_filter_by_due_date_range_ignores_tasks_without_due_date(client, seeded):
    ana, _ = seeded

    assert titles(client, ana.headers, dueBefore="2026-12-01") == ["Relatório", "Vídeo"]
    assert titles(client, ana.headers, dueAfter="2026-11-15") == ["Slides", "Vídeo"]
    assert titles(client, ana.headers, dueAfter="2026-11-15", dueBefore="2026-12-01") == ["Vídeo"]


def test_filters_are_combined(client, seeded):
    ana, bruno = seeded

    result = titles(client, ana.headers, assignedTo=bruno.id, priority="high", status="pending")

    assert result == ["Slides"]


@pytest.mark.parametrize(
    "params",
    [{"status": "finished"}, {"priority": "urgent"}, {"dueBefore": "01/12/2026"}],
)
def test_invalid_filter_values_return_422(client, seeded, params):
    ana, _ = seeded

    response = client.get("/tasks", params=params, headers=ana.headers)

    assert response.status_code == 422
