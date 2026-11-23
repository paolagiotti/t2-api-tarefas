from collections.abc import Iterator

import pytest
from sqlalchemy import Engine

from app.infrastructure.database import build_session_factory
from app.infrastructure.unit_of_work import SqlAlchemyUnitOfWork


@pytest.fixture
def uow(engine: Engine) -> Iterator[SqlAlchemyUnitOfWork]:
    with SqlAlchemyUnitOfWork(build_session_factory(engine)) as unit_of_work:
        yield unit_of_work
