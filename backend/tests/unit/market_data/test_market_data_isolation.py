import ast
from pathlib import Path

MARKET_DATA_ROOT = Path(__file__).resolve().parents[3] / "app" / "market_data"

# Contract modules stay HTTP/WS-free. Venue adapters may use httpx or websockets.
CONTRACT_FILES = {
    "__init__.py",
    "base.py",
    "errors.py",
    "integrity.py",
    "parquet.py",
    "rate_limit.py",
    "reconnect.py",
    "replay.py",
    "stream.py",
    "timeframe.py",
}
VENUE_REST_ADAPTER_FILES = {"bybit.py"}
VENUE_WS_ADAPTER_FILES = {"bybit_ws.py"}

FORBIDDEN_EVERYWHERE = {
    "aiohttp",
    "ccxt",
    "fastapi",
    "redis",
    "requests",
    "sqlalchemy",
    "starlette",
    "urllib",
    "urllib3",
    "uvicorn",
    "websockets",
}
FORBIDDEN_IN_CONTRACT = FORBIDDEN_EVERYWHERE | {"httpx"}


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


def test_contract_modules_do_not_import_network_or_frameworks() -> None:
    offenders: list[str] = []
    for name in sorted(CONTRACT_FILES):
        path = MARKET_DATA_ROOT / name
        imported = _imported_roots(path)
        bad = sorted(imported & FORBIDDEN_IN_CONTRACT)
        if bad:
            offenders.append(f"{path.name}: {', '.join(bad)}")
    assert offenders == []


def test_venue_rest_adapters_may_use_httpx_but_not_ccxt_or_frameworks() -> None:
    offenders: list[str] = []
    for name in sorted(VENUE_REST_ADAPTER_FILES):
        path = MARKET_DATA_ROOT / name
        imported = _imported_roots(path)
        assert "httpx" in imported
        assert "websockets" not in imported
        bad = sorted(imported & FORBIDDEN_EVERYWHERE)
        if bad:
            offenders.append(f"{path.name}: {', '.join(bad)}")
    assert offenders == []


def test_venue_ws_adapters_may_use_websockets_but_not_ccxt_or_frameworks() -> None:
    offenders: list[str] = []
    for name in sorted(VENUE_WS_ADAPTER_FILES):
        path = MARKET_DATA_ROOT / name
        imported = _imported_roots(path)
        assert "websockets" in imported
        bad = sorted((imported & FORBIDDEN_EVERYWHERE) - {"websockets"})
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


def test_parquet_store_may_import_pyarrow_but_not_httpx() -> None:
    imported = _imported_roots(MARKET_DATA_ROOT / "parquet.py")
    assert "pyarrow" in imported
    assert "httpx" not in imported


def test_non_parquet_contract_modules_do_not_import_pyarrow() -> None:
    offenders: list[str] = []
    for name in sorted(CONTRACT_FILES - {"parquet.py"}):
        imported = _imported_roots(MARKET_DATA_ROOT / name)
        if "pyarrow" in imported:
            offenders.append(name)
    assert offenders == []
