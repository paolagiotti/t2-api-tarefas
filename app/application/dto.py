from dataclasses import dataclass, field
from datetime import date, datetime
from uuid import UUID

from app.domain.entities import TaskPriority, TaskStatus, User


@dataclass(frozen=True)
class NewUser:
    name: str
    email: str
    password: str


@dataclass(frozen=True)
class UserChanges:
    """Alteração parcial de usuário: campos None não são alterados.

    `current_password` é exigida apenas para trocar e-mail ou senha.
    """

    name: str | None = None
    email: str | None = None
    password: str | None = None
    current_password: str | None = None


@dataclass(frozen=True)
class NewTask:
    title: str
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: date | None = None
    assigned_to: UUID | None = None


@dataclass(frozen=True)
class TaskChanges:
    """Alteração parcial de tarefa.

    Em `title`, `status` e `priority`, None significa "não alterar".
    Já `description`, `due_date` e `assigned_to` aceitam None como valor (limpar o campo),
    então `provided` indica quais desses campos o cliente realmente enviou.
    """

    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None
    assigned_to: UUID | None = None
    provided: frozenset[str] = field(default_factory=frozenset)

    def has(self, field_name: str) -> bool:
        return field_name in self.provided


@dataclass(frozen=True)
class TaskFilters:
    """Filtros combináveis da listagem de tarefas (campos None são ignorados)."""

    assigned_to: UUID | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_before: date | None = None
    due_after: date | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class IssuedToken:
    access_token: str
    expires_in: int


@dataclass(frozen=True)
class TokenClaims:
    user_id: UUID
    token_id: str
    expires_at: datetime


@dataclass(frozen=True)
class Principal:
    """Usuário autenticado na requisição, junto com os dados do token utilizado."""

    user: User
    claims: TokenClaims
