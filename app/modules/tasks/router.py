"""Esqueleto do modulo de tarefas. Dono: Pessoa B.

Copie a estrutura de app/modules/users/ (schemas -> repository -> service ->
router) e preencha. O contrato de autenticacao ja esta pronto: basta declarar
`user: CurrentUser` no endpoint que o FastAPI resolve o JWT sozinho.
"""
from fastapi import APIRouter

from app.core.security import CurrentUser

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/ping")
def ping(user: CurrentUser):
    """Endpoint temporario so pra provar que a cadeia HTTP -> JWT -> DB funciona."""
    return {"ok": True, "as_user": user.email}
