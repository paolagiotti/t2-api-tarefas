"""Teste unitario: service testado com repository FALSO, sem banco algum.

Isso so e possivel porque o service depende do Protocol, nao da classe
concreta. E a prova pratica do desacoplamento — cite isso na documentacao.
"""
import uuid

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.users.schemas import UserCreate
from app.modules.users.service import UserService


class FakeUserRepository:
    def __init__(self):
        self.items = {}

    def get(self, user_id):
        return self.items.get(user_id)

    def get_by_email(self, email):
        return next((u for u in self.items.values() if u.email == email), None)

    def add(self, user):
        user.id = uuid.uuid4()
        self.items[user.id] = user
        return user

    def save(self, user):
        return user


def test_nao_permite_email_duplicado():
    service = UserService(FakeUserRepository())
    data = UserCreate(name="Paola", email="p@e.com", password="senhaforte123")
    service.create(data)
    with pytest.raises(ConflictError):
        service.create(data)


def test_get_de_usuario_inexistente():
    service = UserService(FakeUserRepository())
    with pytest.raises(NotFoundError):
        service.get(uuid.uuid4())
