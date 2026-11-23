"""Implementações em memória das portas, usadas nos testes de unidade dos casos de uso.

Os repositórios guardam cópias das entidades: assim um teste detecta quando um caso de uso
altera um objeto e esquece de chamar `save`.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.application.dto import IssuedToken, TaskFilters, TokenClaims
from app.application.ports import (
    CommentRepository,
    PasswordHasher,
    RevokedTokenRepository,
    TaskNotifier,
    TaskRepository,
    TokenService,
    UnitOfWork,
    UserRepository,
)
from app.domain.entities import Comment, Task, TaskStatus, User, utc_now
from app.domain.exceptions import AuthenticationError


class InMemoryUserRepository(UserRepository):
    def __init__(self) -> None:
        self.items: dict[UUID, User] = {}

    def add(self, user: User) -> None:
        self.items[user.id] = replace(user)

    def get(self, user_id: UUID) -> User | None:
        user = self.items.get(user_id)
        return replace(user) if user else None

    def get_by_email(self, email: str) -> User | None:
        user = next((u for u in self.items.values() if u.email == email), None)
        return replace(user) if user else None

    def save(self, user: User) -> None:
        self.items[user.id] = replace(user)


class InMemoryTaskRepository(TaskRepository):
    def __init__(self) -> None:
        self.items: dict[UUID, Task] = {}

    def add(self, task: Task) -> None:
        self.items[task.id] = replace(task)

    def get(self, task_id: UUID) -> Task | None:
        task = self.items.get(task_id)
        return replace(task) if task else None

    def save(self, task: Task) -> None:
        self.items[task.id] = replace(task)

    def delete(self, task: Task) -> None:
        del self.items[task.id]

    def find(self, filters: TaskFilters) -> list[Task]:
        tasks = [replace(task) for task in self.items.values() if _matches(task, filters)]
        tasks.sort(key=lambda task: task.created_at, reverse=True)
        return tasks[filters.offset : filters.offset + filters.limit]

    def list_open_assigned_to(self, user_id: UUID) -> list[Task]:
        return [
            replace(task)
            for task in self.items.values()
            if task.assigned_to == user_id and task.status != TaskStatus.DONE
        ]


def _matches(task: Task, filters: TaskFilters) -> bool:
    checks = [
        filters.assigned_to is None or task.assigned_to == filters.assigned_to,
        filters.status is None or task.status == filters.status,
        filters.priority is None or task.priority == filters.priority,
        filters.due_before is None
        or (task.due_date is not None and task.due_date < filters.due_before),
        filters.due_after is None
        or (task.due_date is not None and task.due_date > filters.due_after),
    ]
    return all(checks)


class InMemoryCommentRepository(CommentRepository):
    def __init__(self) -> None:
        self.items: dict[UUID, Comment] = {}

    def add(self, comment: Comment) -> None:
        self.items[comment.id] = replace(comment)

    def get(self, comment_id: UUID) -> Comment | None:
        comment = self.items.get(comment_id)
        return replace(comment) if comment else None

    def list_for_task(self, task_id: UUID) -> list[Comment]:
        comments = [replace(c) for c in self.items.values() if c.task_id == task_id]
        return sorted(comments, key=lambda comment: comment.created_at)

    def delete(self, comment: Comment) -> None:
        del self.items[comment.id]


class InMemoryRevokedTokenRepository(RevokedTokenRepository):
    def __init__(self) -> None:
        self.items: dict[str, datetime] = {}

    def add(self, token_id: str, expires_at: datetime) -> None:
        self.items[token_id] = expires_at

    def contains(self, token_id: str) -> bool:
        return token_id in self.items

    def remove_expired(self, now: datetime) -> int:
        expired = [token_id for token_id, expires_at in self.items.items() if expires_at < now]
        for token_id in expired:
            del self.items[token_id]
        return len(expired)


class InMemoryUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        self.users = InMemoryUserRepository()
        self.tasks = InMemoryTaskRepository()
        self.comments = InMemoryCommentRepository()
        self.revoked_tokens = InMemoryRevokedTokenRepository()
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        pass


class FakePasswordHasher(PasswordHasher):
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed:{password}"


class FakeTokenService(TokenService):
    def __init__(self, ttl: timedelta = timedelta(hours=1)) -> None:
        self._ttl = ttl
        self._issued: dict[str, TokenClaims] = {}

    def issue(self, user_id: UUID) -> IssuedToken:
        claims = TokenClaims(
            user_id=user_id, token_id=uuid4().hex, expires_at=utc_now() + self._ttl
        )
        access_token = f"token-{claims.token_id}"
        self._issued[access_token] = claims
        return IssuedToken(
            access_token=access_token,
            token_id=claims.token_id,
            expires_at=claims.expires_at,
            expires_in=int(self._ttl.total_seconds()),
        )

    def decode(self, token: str) -> TokenClaims:
        try:
            return self._issued[token]
        except KeyError:
            raise AuthenticationError("Token inválido") from None


@dataclass(frozen=True)
class SentNotification:
    kind: str
    task_id: UUID
    recipient_id: UUID
    actor_id: UUID
    changed_fields: tuple[str, ...] = ()


class SpyTaskNotifier(TaskNotifier):
    """Registra as notificações em vez de enviá-las."""

    def __init__(self) -> None:
        self.sent: list[SentNotification] = []

    def task_assigned(self, task: Task, assignee: User, actor: User) -> None:
        self.sent.append(SentNotification("assigned", task.id, assignee.id, actor.id))

    def task_updated(
        self, task: Task, recipient: User, actor: User, changed_fields: Sequence[str]
    ) -> None:
        self.sent.append(
            SentNotification("updated", task.id, recipient.id, actor.id, tuple(changed_fields))
        )
