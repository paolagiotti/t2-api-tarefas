import logging

import pytest

from app.infrastructure.notifications import EmailSender, EmailTaskNotifier
from tests.fakes import SpyTaskNotifier


@pytest.fixture
def notifier(app) -> SpyTaskNotifier:
    spy = SpyTaskNotifier()
    app.state.task_notifier = spy
    return spy


def test_api_notifies_assignee_on_creation_and_creator_on_completion(client, register, notifier):
    ana, bruno = register("Ana"), register("Bruno")

    created = client.post(
        "/tasks", json={"title": "Gravar vídeo", "assignedTo": bruno.id}, headers=ana.headers
    )
    client.put(f"/tasks/{created.json()['id']}", json={"status": "done"}, headers=bruno.headers)

    assert [(sent.kind, str(sent.recipient_id)) for sent in notifier.sent] == [
        ("assigned", bruno.id),
        ("updated", ana.id),
    ]


def test_default_backend_simulates_email_in_the_log(client, register, caplog):
    ana, bruno = register("Ana"), register("Bruno")

    with caplog.at_level(logging.INFO, logger="app.infrastructure.notifications"):
        response = client.post(
            "/tasks", json={"title": "Gravar vídeo", "assignedTo": bruno.id}, headers=ana.headers
        )

    assert response.status_code == 201
    assert "E-mail (simulado) para bruno@example.com" in caplog.text


class BrokenSender(EmailSender):
    def send(self, to: str, subject: str, body: str) -> None:
        raise ConnectionRefusedError("SMTP fora do ar")


def test_email_failure_does_not_affect_the_request(app, client, register, caplog):
    app.state.task_notifier = EmailTaskNotifier(BrokenSender())
    ana, bruno = register("Ana"), register("Bruno")

    with caplog.at_level(logging.ERROR, logger="app.infrastructure.notifications"):
        response = client.post(
            "/tasks", json={"title": "Gravar vídeo", "assignedTo": bruno.id}, headers=ana.headers
        )

    assert response.status_code == 201
    assert client.get(f"/tasks/{response.json()['id']}", headers=ana.headers).status_code == 200
    assert "Falha ao enviar e-mail" in caplog.text
