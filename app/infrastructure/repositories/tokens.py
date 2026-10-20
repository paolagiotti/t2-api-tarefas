from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.application.ports import RevokedTokenRepository
from app.infrastructure.models import RevokedTokenModel


class SqlAlchemyRevokedTokenRepository(RevokedTokenRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, token_id: str, expires_at: datetime) -> None:
        self._session.add(RevokedTokenModel(token_id=token_id, expires_at=expires_at))

    def contains(self, token_id: str) -> bool:
        return self._session.get(RevokedTokenModel, token_id) is not None

    def remove_expired(self, now: datetime) -> int:
        result = self._session.execute(
            delete(RevokedTokenModel).where(RevokedTokenModel.expires_at < now)
        )
        return result.rowcount
