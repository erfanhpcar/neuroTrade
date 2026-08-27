"""API contract tests for the system endpoints.

Dependency checks are faked so unit tests never touch the network or real
services (see ``backend/AGENTS.md`` — prefer fakes over network in unit tests).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import create_app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    async def fake_check_postgres(settings: Settings, timeout: float = 2.0) -> bool:
        return True

    async def fake_check_redis(settings: Settings, timeout: float = 2.0) -> bool:
        return True

    monkeypatch.setattr("app.api.system.check_postgres", fake_check_postgres)
    monkeypatch.setattr("app.api.system.check_redis", fake_check_redis)

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)
    return TestClient(app)


def test_health_ok_when_dependencies_up(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["trading_mode"] == "PAPER"
    assert body["dependencies"] == {"postgres": True, "redis": True}


def test_health_degraded_when_dependency_down(
    monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    async def redis_down(settings: Settings, timeout: float = 2.0) -> bool:
        return False

    monkeypatch.setattr("app.api.system.check_redis", redis_down)
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["dependencies"]["redis"] is False


def test_system_status_reports_paper_default(client: TestClient) -> None:
    response = client.get("/api/system/status")
    assert response.status_code == 200
    body = response.json()
    assert body["trading_mode"] == "PAPER"
    assert body["app_env"] == "development"
