# API de Gestao de Tarefas Colaborativas — T2

Esqueleto da Fase 0: estrutura, core, banco, primeira migration e o modulo
`users` implementado por inteiro como **referencia**. O modulo `tasks` tem so
os models (contrato compartilhado) e um router de exemplo.

## Como rodar

```bash
cp .env.example .env
docker compose up --build          # sobe Postgres + API, aplica migrations
# http://localhost:8000/docs  -> Swagger gerado automaticamente
```

Sem Docker (so pra rodar testes, usa SQLite em memoria):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest
```

## O caminho de uma requisicao

```
POST /users
  -> app/modules/users/router.py      traduz HTTP, valida com Pydantic
  -> app/modules/users/service.py     regra de negocio (email unico, hash)
  -> app/modules/users/repository.py  unico lugar que fala SQLAlchemy
  -> app/modules/users/models.py      tabela
```

Regra de ouro: `service.py` nao importa `fastapi` nem `sqlalchemy`. Se um
import desses aparecer la, a regra de negocio vazou pra fora da camada.

## Estrutura

```
app/
├── main.py                  monta a aplicacao (factory create_app)
├── core/
│   ├── config.py            unico lugar que le variaveis de ambiente
│   ├── exceptions.py        erros de dominio + tradutor pra HTTP
│   ├── logging.py           log JSON + request_id por requisicao
│   └── security.py          hash, JWT, get_current_user, require_role
├── db/
│   ├── base.py              Base declarativa + TimestampMixin
│   ├── session.py           engine, SessionLocal, dependency get_db
│   ├── registry.py          importa todos os models (Alembic depende disso)
│   └── migrations/          Alembic
└── modules/
    ├── users/               COMPLETO — use como molde
    └── tasks/               esqueleto (Pessoa B)
tests/
├── conftest.py              SQLite em memoria + override de get_db
├── unit/                    service com repository falso, sem banco
└── integration/             API real via TestClient
```

## Comandos uteis

```bash
# nova migration depois de mexer num model
alembic revision --autogenerate -m "adiciona tabela comments"
alembic upgrade head
alembic downgrade -1

pytest                       # ja falha se a cobertura cair abaixo de 60%
pytest --cov-report=html     # relatorio navegavel em htmlcov/index.html
```

## Divisao do trabalho

| Pessoa A — Identidade e Seguranca | Pessoa B — Dominio de Tarefas |
|---|---|
| `modules/users/` (CRUD + soft delete) | `modules/tasks/` (CRUD + atribuicao) |
| `modules/auth/` (login JWT, logout) | Req. 8: filtros avancados |
| `core/security.py` | Req. 6: `modules/comments/` |
| Req. 5: papeis e permissoes | fixtures + testes de integracao |
| testes de users/auth | CI (GitHub Actions) |

**Contrato entre as duas:** a Pessoa B so depende de `CurrentUser` e
`require_role` (`app/core/security.py`). Enquanto a A nao termina, a B
sobrescreve `get_current_user` no `conftest.py` com um usuario fixo e segue.

## Decisoes ja tomadas (levar pra documentacao)

- **Camadas com Repository Pattern** em vez de Hexagonal pura: mesmo ganho de
  desacoplamento com menos cerimonia, viavel no prazo de uma dupla.
- **Modulos verticais** (por dominio, nao por camada): reduz conflito de merge
  porque cada pessoa mexe nas suas pastas.
- **Postgres**: dados fortemente relacionais (user ↔ task ↔ comment), com
  integridade referencial e agregacoes para as metricas de produtividade.
- **UUID como PK**: ids nao sequenciais nao vazam volume de dados nem permitem
  enumeracao de recursos pela URL.
- **Soft delete**: `DELETE /users/{id}` marca `is_active = False`, preservando
  o historico de tarefas criadas por aquele usuario.
- **Erros de dominio + handler unico**: respostas de erro padronizadas
  (`{"error": {"code", "message"}}`) sem espalhar `HTTPException` pelo codigo.
