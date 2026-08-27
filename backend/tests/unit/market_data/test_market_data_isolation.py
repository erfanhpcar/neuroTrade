import ast
from pathlib import Path

MARKET_DATA_ROOT = Path(__file__).resolve().parents[3] / "app" / "market_data"

FORBIDDEN_MODULES = {
    "aiohttp",
    "ccxt",
    "fastapi",
    "httpx",
    "redis",
    "requests",
    "sqlalchemy",
    "starlette",
    "urllib",
    "urllib3",
    "uvicorn",
    "websockets",
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


def test_market_data_package_does_not_import_network_or_frameworks() -> None:
    offenders: list[str] = []
    for path in sorted(MARKET_DATA_ROOT.glob("*.py")):
        imported = _imported_roots(path)
        bad = sorted(imported & FORBIDDEN_MODULES)
        if bad:
            offenders.append(f"{path.name}: {', '.join(bad)}")
    assert offenders == []


def test_market_data_package_does_not_import_execution_or_control_plane() -> None:
    for path in sorted(MARKET_DATA_ROOT.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("app.execution")
                assert not node.module.startswith("app.strategies")
                assert not node.module.startswith("app.workers")
                assert not node.module.startswith("app.api")
                assert not node.module.startswith("app.main")
                assert not node.module.startswith("app.infrastructure")
                assert not node.module.startswith("app.config")
