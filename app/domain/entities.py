import unicodedata
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.exceptions import BusinessRuleViolation

USER_NAME_MAX_LENGTH = 120
TASK_TITLE_MAX_LENGTH = 200
TASK_DESCRIPTION_MAX_LENGTH = 5000
COMMENT_MAX_LENGTH = 2000


def utc_now() -> datetime:
    return datetime.now(UTC)


def normalize_email(email: str) -> str:
    return email.strip().lower()


class TaskStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(kw_only=True)
class User:
    name: str
    email: str
    password_hash: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        self.rename(self.name)
        self.change_email(self.email)

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    def rename(self, name: str) -> None:
        self.name = _single_line_text(name, "o nome do usuário", USER_NAME_MAX_LENGTH)

    def change_email(self, email: str) -> None:
        self.email = normalize_email(email)

    def touch(self) -> None:
        self.updated_at = utc_now()

    def deactivate(self) -> None:
        """Remoção lógica (soft delete): o registro é mantido para preservar o histórico."""
        if self.is_active:
            self.deleted_at = utc_now()
            self.updated_at = self.deleted_at


@dataclass(kw_only=True)
class Task:
    title: str
    created_by: UUID
    description: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None
    assigned_to: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        self.rename(self.title)
        self.describe(self.description)

    def rename(self, title: str) -> None:
        self.title = _single_line_text(title, "o título da tarefa", TASK_TITLE_MAX_LENGTH)

    def describe(self, description: str | None) -> None:
        """Texto livre; vazio equivale a não ter descrição."""
        text = (description or "").strip()
        _check_length(text, "a descrição da tarefa", TASK_DESCRIPTION_MAX_LENGTH)
        self.description = text or None

    def change_status(self, status: TaskStatus) -> None:
        if status == self.status:
            return
        self.status = status
        self.completed_at = utc_now() if status == TaskStatus.DONE else None

    def assign_to(self, user_id: UUID | None) -> None:
        self.assigned_to = user_id

    def can_be_edited_by(self, user_id: UUID) -> bool:
        return user_id in (self.created_by, self.assigned_to)

    def can_be_deleted_by(self, user_id: UUID) -> bool:
        return user_id == self.created_by

    def touch(self) -> None:
        self.updated_at = utc_now()


@dataclass(kw_only=True)
class Comment:
    task_id: UUID
    author_id: UUID
    content: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        self.content = self.content.strip()
        if not self.content:
            raise BusinessRuleViolation("O comentário não pode ser vazio")
        _check_length(self.content, "o comentário", COMMENT_MAX_LENGTH)

    def can_be_deleted_by(self, user_id: UUID) -> bool:
        return user_id == self.author_id


def _single_line_text(value: str, label: str, max_length: int) -> str:
    """Normaliza textos curtos, como nomes e títulos, que também vão para o assunto dos e-mails:
    quebras de linha, tabulações e espaços repetidos viram um único espaço."""
    text = " ".join(value.split())
    if not text:
        raise BusinessRuleViolation(f"{_capitalized(label)} é obrigatório")
    if any(unicodedata.category(char) == "Cc" for char in text):
        raise BusinessRuleViolation(f"{_capitalized(label)} não pode conter caracteres de controle")
    _check_length(text, label, max_length)
    return text


def _check_length(text: str, label: str, max_length: int) -> None:
    if len(text) > max_length:
        raise BusinessRuleViolation(
            f"{_capitalized(label)} deve ter no máximo {max_length} caracteres"
        )


def _capitalized(label: str) -> str:
    return label[:1].upper() + label[1:]
