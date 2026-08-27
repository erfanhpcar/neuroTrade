import ast
from pathlib import Path

from app.infrastructure.db.engine import redact_database_url

INFRA_DB = Path(__file__).resolve().parents[3] / "app" / "infrastructure" / "db"

FORBIDDEN = {"fastapi", "starlette", "ccxt", "redis", "httpx", "uvicorn"}


def test_db_package_does_not_import_web_or_exchange_clients() -> None:
    offenders: list[str] = []
    for path in sorted(INFRA_DB.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        bad = sorted(imported & FORBIDDEN)
        if bad:
            offenders.append(f"{path.name}: {', '.join(bad)}")
    assert offenders == []


def test_redact_database_url_hides_password() -> None:
    redacted = redact_database_url(
        "postgresql+asyncpg://neurotrade:neurotrade_dev_password@localhost:5432/neurotrade"
    )
    assert "neurotrade_dev_password" not in redacted
    assert "localhost:5432" in redacted
    assert "neurotrade" in redacted
