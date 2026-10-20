from collections.abc import Callable

import pytest

from app.application.use_cases.tasks import CreateTask, UpdateTask
from app.domain.entities import User
from tests.fakes import FakePasswordHasher, FakeTokenService, InMemoryUnitOfWork


@pytest.fixture
def uow() -> InMemoryUnitOfWork:
    return InMemoryUnitOfWork()


@pytest.fixture
def hasher() -> FakePasswordHasher:
    return FakePasswordHasher()


@pytest.fixture
def tokens() -> FakeTokenService:
    return FakeTokenService()


@pytest.fixture
def make_user(uow: InMemoryUnitOfWork, hasher: FakePasswordHasher) -> Callable[..., User]:
    def _make_user(name: str = "Ana", password: str = "senha-segura") -> User:
        user = User(
            name=name,
            email=f"{name.lower()}@example.com",
            password_hash=hasher.hash(password),
        )
        uow.users.add(user)
        return user

    return _make_user


@pytest.fixture
def create_task(uow: InMemoryUnitOfWork) -> CreateTask:
    return CreateTask(uow)


@pytest.fixture
def update_task(uow: InMemoryUnitOfWork) -> UpdateTask:
    return UpdateTask(uow)
