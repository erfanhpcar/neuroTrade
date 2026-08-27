from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_PATH = REPO_ROOT / "docker-compose.yml"


def _compose_text() -> str:
    return COMPOSE_PATH.read_text(encoding="utf-8")


def test_compose_file_exists() -> None:
    assert COMPOSE_PATH.is_file()


def test_compose_defines_required_services() -> None:
    text = _compose_text()
    for service in ("postgres:", "redis:", "backend:", "trading-worker:", "frontend:"):
        assert f"  {service}" in text


def test_compose_defaults_trading_mode_to_paper() -> None:
    text = _compose_text()
    assert "TRADING_MODE: ${TRADING_MODE:-PAPER}" in text
    assert "TRADING_MODE: FULL" not in text
    assert "TRADING_MODE=FULL" not in text


def test_compose_does_not_expose_backend_via_next_public() -> None:
    text = _compose_text()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or not stripped:
            continue
        assert "NEXT_PUBLIC" not in stripped


def test_compose_keeps_postgres_and_redis_on_internal_hostnames() -> None:
    text = _compose_text()
    assert "@postgres:5432/neurotrade" in text
    assert "REDIS_URL: redis://redis:6379/0" in text
    assert "BACKEND_URL: http://host.docker.internal:8000" in text
    assert "host.docker.internal:host-gateway" in text


def test_compose_worker_uses_heartbeat_module_not_uvicorn() -> None:
    text = _compose_text()
    assert "app.workers.trading_worker" in text
    worker_block = text.split("trading-worker:")[1].split("frontend:")[0]
    assert "uvicorn" not in worker_block


def test_backend_and_frontend_dockerfiles_exist() -> None:
    assert (REPO_ROOT / "backend" / "Dockerfile").is_file()
    assert (REPO_ROOT / "frontend" / "Dockerfile").is_file()
