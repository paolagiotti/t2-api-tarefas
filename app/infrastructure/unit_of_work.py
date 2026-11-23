from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.application.ports import UnitOfWork
from app.domain.exceptions import ConflictError
from app.infrastructure.repositories.comments import SqlAlchemyCommentRepository
from app.infrastructure.repositories.tasks import SqlAlchemyTaskRepository
from app.infrastructure.repositories.tokens import SqlAlchemyRevokedTokenRepository
from app.infrastructure.repositories.users import SqlAlchemyUserRepository


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Uma sessão do SQLAlchemy por operação; `commit` confirma tudo em uma transação."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session = session_factory()
        self.users = SqlAlchemyUserRepository(self._session)
        self.tasks = SqlAlchemyTaskRepository(self._session)
        self.comments = SqlAlchemyCommentRepository(self._session)
        self.revoked_tokens = SqlAlchemyRevokedTokenRepository(self._session)

    def commit(self) -> None:
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("A operação viola uma restrição de integridade dos dados") from exc

    def close(self) -> None:
        self._session.close()
