class DomainError(Exception):
    """Erro de regra de negócio. Não conhece HTTP nem banco de dados."""


class NotFoundError(DomainError):
    """O recurso solicitado não existe (ou foi removido)."""


class ConflictError(DomainError):
    """A operação conflita com o estado atual dos dados (ex.: e-mail já cadastrado)."""


class PermissionDeniedError(DomainError):
    """O usuário autenticado não pode executar a operação."""


class AuthenticationError(DomainError):
    """Credenciais ou token inválidos."""


class BusinessRuleViolation(DomainError):
    """Os dados informados violam uma regra de negócio."""
