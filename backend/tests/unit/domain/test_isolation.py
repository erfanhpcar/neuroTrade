import ast
from pathlib import Path

DOMAIN_ROOT = Path(__file__).resolve().parents[3] / "app" / "domain"

FORBIDDEN_MODULES = {
    "fastapi",
    "starlette",
    "sqlalchemy",
    "alembic",
    "ccxt",
    "redis",
    "httpx",
    "uvicorn",
    "pydantic",
    "pydantic_settings",
}


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_domain_package_does_not_import_frameworks() -> None:
    offenders: list[str] = []
    for path in sorted(DOMAIN_ROOT.glob("*.py")):
        imported = _imported_roots(path)
        bad = sorted(imported & FORBIDDEN_MODULES)
        if bad:
            offenders.append(f"{path.name}: {', '.join(bad)}")
    assert offenders == []


def test_domain_package_does_not_import_execution_or_workers() -> None:
    for path in sorted(DOMAIN_ROOT.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("app.execution")
                assert not node.module.startswith("app.workers")
                assert not node.module.startswith("app.api")
                assert not node.module.startswith("app.main")
