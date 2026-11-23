"""Gera docs/openapi.json a partir da própria aplicação.

Uso (na raiz do projeto): python -m scripts.export_openapi
"""

import json
from pathlib import Path

from app.config import Settings
from app.main import create_app

OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "openapi.json"


def main() -> None:
    # Só a especificação é gerada: nenhuma conexão com banco ou SMTP é aberta.
    settings = Settings(_env_file=None, database_url="sqlite://", jwt_secret="x" * 32)
    spec = create_app(settings).openapi()

    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Especificação OpenAPI gravada em {OUTPUT.relative_to(Path.cwd())}")


if __name__ == "__main__":
    main()
