from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.application.ports import UnitOfWork
from app.domain.exceptions import ConflictError
from app.infrastructure.repositories.tasks import SqlAlchemyTaskRepository
from app.infrastructure.repositories.tokens import SqlAlchemyRevokedTokenRepository
from app.infrastructure.repositories.users import SqlAlchemyUserRepository


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Uma sessão do SQLAlchemy por requisição; `commit` confirma tudo em uma transação."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self.users = SqlAlchemyUserRepository(session)
        self.tasks = SqlAlchemyTaskRepository(session)
        self.revoked_tokens = SqlAlchemyRevokedTokenRepository(session)

    def commit(self) -> None:
        try:
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise ConflictError("A operação viola uma restrição de integridade dos dados") from exc
