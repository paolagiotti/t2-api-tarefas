# API de Gestão de Tarefas Colaborativas

Trabalho T2 da atividade acadêmica **Engenharia de Software – Arquitetura e Padrões** (Unisinos).

API REST em Python (FastAPI) para criação, atribuição e acompanhamento de tarefas em equipe,
organizada segundo a Clean Architecture.

## Executando com Docker (recomendado)

Requisitos: Docker com Docker Compose.

```bash
docker compose up --build
```

Isso sobe o PostgreSQL, aplica as migrações e inicia a API em http://localhost:8000.
A documentação interativa (Swagger UI) fica em http://localhost:8000/docs.

## Executando localmente

Requisitos: Python 3.12 ou superior.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
docker compose up -d db        # ou ajuste DATABASE_URL no .env para usar SQLite
alembic upgrade head
uvicorn app.main:create_app --factory --reload
```

## Testes

```bash
pytest --cov
```
