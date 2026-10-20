"""Garante a regra de dependência da Clean Architecture: camadas internas não importam
camadas externas nem frameworks."""

import ast
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1] / "app"

FORBIDDEN_IMPORTS = {
    "domain": ("app.application", "app.infrastructure", "app.api", "fastapi", "sqlalchemy"),
    "application": ("app.infrastructure", "app.api", "fastapi", "sqlalchemy", "pydantic"),
}


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


@pytest.mark.parametrize("layer", sorted(FORBIDDEN_IMPORTS))
def test_inner_layer_does_not_depend_on_outer_layers(layer):
    violations = [
        f"{path.relative_to(APP_DIR)} importa {module}"
        for path in sorted((APP_DIR / layer).rglob("*.py"))
        for module in imported_modules(path)
        if module.startswith(FORBIDDEN_IMPORTS[layer])
    ]

    assert not violations, "\n".join(violations)
