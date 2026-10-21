"""Notificações de tarefas por e-mail.

`EmailTaskNotifier` implementa a porta `TaskNotifier` e monta as mensagens. O envio em si é
delegado a um `EmailSender`: SMTP de verdade ou apenas um registro no log.
"""

import logging
import smtplib
import ssl
from abc import ABC, abstractmethod
from collections.abc import Sequence
from email.message import EmailMessage

from app.application.ports import TaskNotifier
from app.domain.entities import Task, TaskPriority, TaskStatus, User

logger = logging.getLogger(__name__)

STATUS_LABELS = {
    TaskStatus.PENDING: "Pendente",
    TaskStatus.IN_PROGRESS: "Em andamento",
    TaskStatus.DONE: "Concluída",
}
PRIORITY_LABELS = {
    TaskPriority.LOW: "Baixa",
    TaskPriority.MEDIUM: "Média",
    TaskPriority.HIGH: "Alta",
}
FIELD_LABELS = {
    "title": "título",
    "description": "descrição",
    "status": "status",
    "priority": "prioridade",
    "due_date": "prazo",
    "assigned_to": "responsável",
}


class EmailSender(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, body: str) -> None: ...


class SmtpEmailSender(EmailSender):
    def __init__(
        self,
        host: str,
        port: int,
        sender: str,
        *,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = False,
        timeout: float = 10.0,
    ) -> None:
        if username and not use_tls:
            raise ValueError("Autenticação SMTP exige TLS: defina SMTP_USE_TLS=true")
        self._host = host
        self._port = port
        self._sender = sender
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._timeout = timeout

    def send(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self._sender
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
            if self._use_tls:
                smtp.starttls(context=ssl.create_default_context())
            if self._username:
                smtp.login(self._username, self._password or "")
            smtp.send_message(message)


class LogEmailSender(EmailSender):
    """Simula o envio registrando o e-mail no log (útil quando não há servidor SMTP)."""

    def send(self, to: str, subject: str, body: str) -> None:
        logger.info("E-mail (simulado) para %s | %s\n%s", to, subject, body)


class EmailTaskNotifier(TaskNotifier):
    def __init__(self, sender: EmailSender) -> None:
        self._sender = sender

    def task_assigned(self, task: Task, assignee: User, actor: User) -> None:
        self._deliver(
            assignee,
            subject=f"Nova tarefa atribuída a você: {task.title}",
            body=(
                f"Olá, {assignee.name}!\n\n"
                f"{actor.name} atribuiu uma tarefa a você.\n\n"
                f"{_summary(task)}"
            ),
        )

    def task_updated(
        self, task: Task, recipient: User, actor: User, changed_fields: Sequence[str]
    ) -> None:
        changes = ", ".join(FIELD_LABELS.get(name, name) for name in changed_fields)
        self._deliver(
            recipient,
            subject=f"Tarefa atualizada: {task.title}",
            body=(
                f"Olá, {recipient.name}!\n\n"
                f"{actor.name} alterou a tarefa ({changes}).\n\n"
                f"{_summary(task)}"
            ),
        )

    def _deliver(self, recipient: User, subject: str, body: str) -> None:
        # Cumpre o contrato da porta: a tarefa já foi salva, então qualquer falha no envio
        # (servidor fora do ar, mensagem malformada...) é registrada e não chega ao cliente.
        try:
            self._sender.send(recipient.email, subject, body)
        except Exception:
            logger.exception("Falha ao enviar e-mail para o usuário %s", recipient.id)
        else:
            logger.info("E-mail enviado para o usuário %s: %s", recipient.id, subject)


def _summary(task: Task) -> str:
    due_date = task.due_date.strftime("%d/%m/%Y") if task.due_date else "sem prazo"
    lines = [
        f"Tarefa: {task.title}",
        f"Status: {STATUS_LABELS[task.status]}",
        f"Prioridade: {PRIORITY_LABELS[task.priority]}",
        f"Prazo: {due_date}",
    ]
    if task.description:
        lines.append(f"Descrição: {task.description}")
    return "\n".join(lines) + "\n"
