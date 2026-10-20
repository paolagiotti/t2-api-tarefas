"""Implementações em memória das portas, usadas nos testes de unidade dos casos de uso.

Os repositórios guardam cópias das entidades: assim um teste detecta quando um caso de uso
altera um objeto e esquece de chamar `save`.
"""

from dataclasses import replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from app.application.dto import IssuedToken, TaskFilters, TokenClaims
from app.application.ports import (
    PasswordHasher,
    RevokedTokenRepository,
    TaskRepository,
    TokenService,
    UnitOfWork,
    UserRepository,
)
from app.domain.entities import Task, User, utc_now
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
        self.revoked_tokens = InMemoryRevokedTokenRepository()
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


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
