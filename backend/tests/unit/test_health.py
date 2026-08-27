import json
import logging

from app.config import TradingMode
from app.infrastructure.logging import JsonLogFormatter, RequestIdFilter, request_id_ctx
from app.main import REQUEST_ID_HEADER


def test_health_returns_ok_and_paper_mode(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "ok",
        "service": "control-plane",
        "trading_mode": TradingMode.PAPER.value,
        "app_env": "development",
    }


def test_health_echoes_incoming_request_id(client) -> None:
    response = client.get("/api/health", headers={REQUEST_ID_HEADER: "req-test-1"})
    assert response.headers[REQUEST_ID_HEADER] == "req-test-1"


def test_health_generates_request_id_when_missing(client) -> None:
    response = client.get("/api/health")
    request_id = response.headers.get(REQUEST_ID_HEADER)
    assert request_id is not None
    assert request_id != ""


def test_json_formatter_includes_request_id() -> None:
    token = request_id_ctx.set("corr-123")
    try:
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="health ok",
            args=(),
            exc_info=None,
        )
        RequestIdFilter().filter(record)
        payload = json.loads(JsonLogFormatter().format(record))
    finally:
        request_id_ctx.reset(token)

    assert payload["message"] == "health ok"
    assert payload["request_id"] == "corr-123"
    assert payload["level"] == "INFO"
    assert "timestamp" in payload
