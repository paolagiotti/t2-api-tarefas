"""Portas: interfaces que a camada de aplicação exige do mundo externo.

As implementações concretas (banco de dados, bcrypt, JWT, e-mail) ficam em app.infrastructure,
o que mantém os casos de uso independentes de frameworks.
"""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from app.application.dto import IssuedToken, TaskFilters, TokenClaims
from app.domain.entities import Comment, Task, User


class UserRepository(ABC):
    @abstractmethod
    def add(self, user: User) -> None: ...

    @abstractmethod
    def get(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    def save(self, user: User) -> None: ...


class TaskRepository(ABC):
    @abstractmethod
    def add(self, task: Task) -> None: ...

    @abstractmethod
    def get(self, task_id: UUID) -> Task | None: ...

    @abstractmethod
    def save(self, task: Task) -> None: ...

    @abstractmethod
    def delete(self, task: Task) -> None: ...

    @abstractmethod
    def find(self, filters: TaskFilters) -> list[Task]: ...


class CommentRepository(ABC):
    @abstractmethod
    def add(self, comment: Comment) -> None: ...

    @abstractmethod
    def get(self, comment_id: UUID) -> Comment | None: ...

    @abstractmethod
    def list_for_task(self, task_id: UUID) -> list[Comment]: ...

    @abstractmethod
    def delete(self, comment: Comment) -> None: ...


class RevokedTokenRepository(ABC):
    @abstractmethod
    def add(self, token_id: str, expires_at: datetime) -> None: ...

    @abstractmethod
    def contains(self, token_id: str) -> bool: ...

    @abstractmethod
    def remove_expired(self, now: datetime) -> int: ...


class UnitOfWork(ABC):
    """Reúne os repositórios de uma operação e confirma as alterações em uma única transação."""

    users: UserRepository
    tasks: TaskRepository
    comments: CommentRepository
    revoked_tokens: RevokedTokenRepository

    @abstractmethod
    def commit(self) -> None: ...


class PasswordHasher(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, password: str, password_hash: str) -> bool: ...


class TokenService(ABC):
    @abstractmethod
    def issue(self, user_id: UUID) -> IssuedToken: ...

    @abstractmethod
    def decode(self, token: str) -> TokenClaims:
        """Lança AuthenticationError se o token for inválido ou estiver expirado."""


class TaskNotifier(ABC):
    """Avisa os envolvidos em uma tarefa sobre atribuições e alterações (e-mail, push, log...)."""

    @abstractmethod
    def task_assigned(self, task: Task, assignee: User, actor: User) -> None: ...

    @abstractmethod
    def task_updated(
        self, task: Task, recipient: User, actor: User, changed_fields: Sequence[str]
    ) -> None: ...
