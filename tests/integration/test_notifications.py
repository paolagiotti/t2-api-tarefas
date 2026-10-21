import logging
import smtplib
import ssl
from datetime import date
from typing import ClassVar

import pytest

from app.domain.entities import Task, TaskPriority, TaskStatus, User
from app.infrastructure.notifications import (
    EmailSender,
    EmailTaskNotifier,
    LogEmailSender,
    SmtpEmailSender,
)
from app.main import build_task_notifier


class RecordingSender(EmailSender):
    def __init__(self, error: Exception | None = None) -> None:
        self.messages: list[tuple[str, str, str]] = []
        self._error = error

    def send(self, to: str, subject: str, body: str) -> None:
        if self._error is not None:
            raise self._error
        self.messages.append((to, subject, body))


class FakeSMTP:
    """Substitui smtplib.SMTP e guarda o que seria enviado."""

    instances: ClassVar[list["FakeSMTP"]] = []

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host, self.port, self.timeout = host, port, timeout
        self.calls: list[tuple] = []
        self.messages = []
        FakeSMTP.instances.append(self)

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *exc_info) -> None:
        return None

    def starttls(self, context: ssl.SSLContext | None = None) -> None:
        verified = context is not None and context.verify_mode == ssl.CERT_REQUIRED
        self.calls.append(("starttls", verified))

    def login(self, username: str, password: str) -> None:
        self.calls.append(("login", username, password))

    def send_message(self, message) -> None:
        self.messages.append(message)


@pytest.fixture
def fake_smtp(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


@pytest.fixture
def people() -> tuple[User, User]:
    return (
        User(name="Ana", email="ana@example.com", password_hash="x"),
        User(name="Bruno", email="bruno@example.com", password_hash="x"),
    )


def make_task(creator: User, assignee: User) -> Task:
    return Task(
        title="Gravar vídeo",
        description="Até 15 minutos",
        priority=TaskPriority.HIGH,
        due_date=date(2026, 11, 30),
        created_by=creator.id,
        assigned_to=assignee.id,
    )


def test_assignment_email_describes_the_task(people):
    ana, bruno = people
    sender = RecordingSender()

    EmailTaskNotifier(sender).task_assigned(make_task(ana, bruno), bruno, ana)

    [(to, subject, body)] = sender.messages
    assert to == "bruno@example.com"
    assert subject == "Nova tarefa atribuída a você: Gravar vídeo"
    assert "Ana atribuiu uma tarefa a você" in body
    assert "Prioridade: Alta" in body
    assert "Prazo: 30/11/2026" in body
    assert "Descrição: Até 15 minutos" in body


def test_update_email_lists_changed_fields(people):
    ana, bruno = people
    task = make_task(ana, bruno)
    task.change_status(TaskStatus.DONE)
    sender = RecordingSender()

    EmailTaskNotifier(sender).task_updated(task, ana, bruno, ["status", "due_date"])

    [(to, subject, body)] = sender.messages
    assert to == "ana@example.com"
    assert subject == "Tarefa atualizada: Gravar vídeo"
    assert "Bruno alterou a tarefa (status, prazo)" in body
    assert "Status: Concluída" in body


@pytest.mark.parametrize(
    "error",
    [ConnectionRefusedError("SMTP indisponível"), ValueError("cabeçalho inválido")],
    ids=["servidor-fora-do-ar", "mensagem-invalida"],
)
def test_delivery_failure_is_logged_without_raising(people, caplog, error):
    ana, bruno = people
    sender = RecordingSender(error=error)

    with caplog.at_level(logging.ERROR, logger="app.infrastructure.notifications"):
        EmailTaskNotifier(sender).task_assigned(make_task(ana, bruno), bruno, ana)

    assert "Falha ao enviar e-mail" in caplog.text


def test_smtp_sender_uses_tls_and_login_when_configured(fake_smtp):
    sender = SmtpEmailSender(
        "smtp.example.com",
        587,
        "Tarefas <nao-responda@example.com>",
        username="usuario",
        password="senha",
        use_tls=True,
        timeout=5,
    )

    sender.send("ana@example.com", "Assunto", "Corpo da mensagem")

    [smtp] = fake_smtp.instances
    [message] = smtp.messages
    assert (smtp.host, smtp.port, smtp.timeout) == ("smtp.example.com", 587, 5)
    assert smtp.calls == [("starttls", True), ("login", "usuario", "senha")]
    assert message["To"] == "ana@example.com"
    assert message["From"] == "Tarefas <nao-responda@example.com>"
    assert message["Subject"] == "Assunto"
    assert message.get_content().strip() == "Corpo da mensagem"


def test_smtp_login_without_tls_is_rejected():
    with pytest.raises(ValueError, match="TLS"):
        SmtpEmailSender("smtp.example.com", 587, "x@example.com", username="u", password="p")


def test_log_sender_writes_the_email_to_the_log(caplog):
    with caplog.at_level(logging.INFO, logger="app.infrastructure.notifications"):
        LogEmailSender().send("ana@example.com", "Assunto", "Corpo")

    assert "E-mail (simulado) para ana@example.com | Assunto" in caplog.text


def test_smtp_backend_is_built_from_settings(settings, people, fake_smtp):
    smtp_settings = settings.model_copy(
        update={"notification_backend": "smtp", "smtp_host": "mailpit", "smtp_port": 1025}
    )
    ana, bruno = people

    build_task_notifier(smtp_settings).task_assigned(make_task(ana, bruno), bruno, ana)

    [smtp] = fake_smtp.instances
    assert (smtp.host, smtp.port) == ("mailpit", 1025)
    assert smtp.calls == []
    assert smtp.messages[0]["To"] == "bruno@example.com"
