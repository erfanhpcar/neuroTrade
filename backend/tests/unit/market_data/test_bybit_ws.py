import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.domain.errors import InvalidFinancialValue
from app.market_data.bybit_ws import (
    BYBIT_DEFAULT_WS_BASE_URL,
    BybitPublicWsStream,
    bybit_public_ws_url,
    parse_bybit_ws_message,
    run_heartbeat,
)
from app.market_data.errors import MarketDataStreamDisconnected, MarketDataStreamError
from app.market_data.reconnect import ReconnectPolicy
from app.market_data.stream import LiveCandleUpdate, LiveMarketDataStream, LiveTicker, closed_bar


class FakeClock:
    def __init__(self, start: float = 1_000.0) -> None:
        self.now = start
        self.sleeps: list[float] = []

    async def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


class FakeSocket:
    def __init__(self, incoming: list[str | BaseException]) -> None:
        self.sent: list[str] = []
        self.incoming = list(incoming)
        self.closed = False

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def recv(self) -> str:
        if not self.incoming:
            raise ConnectionError("fake socket exhausted")
        item = self.incoming.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    async def close(self) -> None:
        self.closed = True


class FakeConnector:
    def __init__(self, sockets: list[FakeSocket]) -> None:
        self.sockets = list(sockets)
        self.urls: list[str] = []

    async def __call__(self, url: str) -> FakeSocket:
        self.urls.append(url)
        if not self.sockets:
            raise ConnectionError("no fake sockets remaining")
        return self.sockets.pop(0)


def _ts_ms(hour: int) -> int:
    return int(datetime(2026, 8, 1, hour, 0, tzinfo=UTC).timestamp() * 1000)


def _subscribe_ack(*, success: bool = True) -> str:
    return json.dumps({"success": success, "ret_msg": "subscribe", "op": "subscribe"})


def _ticker_payload(*, last_price: str = "65100.50", msg_type: str = "snapshot") -> str:
    return json.dumps(
        {
            "topic": "tickers.BTCUSDT",
            "ts": _ts_ms(12),
            "type": msg_type,
            "cs": 1,
            "data": {
                "symbol": "BTCUSDT",
                "lastPrice": last_price,
                "volume24h": "1.25",
            },
        }
    )


def _kline_payload(*, confirm: bool, close: str = "65100.50") -> str:
    start = _ts_ms(8)
    return json.dumps(
        {
            "topic": "kline.240.BTCUSDT",
            "ts": _ts_ms(12),
            "type": "snapshot",
            "data": [
                {
                    "start": start,
                    "end": start + 4 * 60 * 60 * 1000 - 1,
                    "interval": "240",
                    "open": "65000.00",
                    "close": close,
                    "high": "65300.00",
                    "low": "64900.00",
                    "volume": "1.25",
                    "turnover": "81250.00",
                    "confirm": confirm,
                    "timestamp": _ts_ms(12),
                }
            ],
        }
    )


def _stream(connector: FakeConnector, **kwargs: Any) -> tuple[BybitPublicWsStream, FakeClock]:
    clock = FakeClock()
    return BybitPublicWsStream(
        connector=connector,
        ping_interval_seconds=0,
        rng=lambda: 0.0,
        sleeper=clock.sleep,
        reconnect=kwargs.pop("reconnect", ReconnectPolicy(max_attempts=1, jitter_ratio=0.0)),
        **kwargs,
    ), clock


async def _collect(stream: BybitPublicWsStream, count: int) -> list[object]:
    events: list[object] = []
    async for event in stream.subscribe("BTC/USDT", "4h"):
        events.append(event)
        if len(events) >= count:
            break
    return events


def test_public_ws_url_matches_official_spot_and_linear_paths() -> None:
    assert (
        bybit_public_ws_url("spot", base_url=BYBIT_DEFAULT_WS_BASE_URL)
        == "wss://stream.bybit.com/v5/public/spot"
    )
    assert bybit_public_ws_url("linear") == "wss://stream.bybit.com/v5/public/linear"


def test_parse_ticker_uses_decimal_and_utc() -> None:
    events = parse_bybit_ws_message(
        _ticker_payload(),
        provider="bybit",
        symbol="BTC/USDT",
        timeframe="4h",
        venue_symbol="BTCUSDT",
    )
    assert len(events) == 1
    ticker = events[0]
    assert isinstance(ticker, LiveTicker)
    assert ticker.last_price == Decimal("65100.50")
    assert ticker.timestamp == datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
    assert ticker.symbol == "BTC/USDT"


def test_unconfirmed_kline_is_not_a_closed_bar() -> None:
    events = parse_bybit_ws_message(
        _kline_payload(confirm=False),
        provider="bybit",
        symbol="BTC/USDT",
        timeframe="4h",
        venue_symbol="BTCUSDT",
    )
    assert len(events) == 1
    candle = events[0]
    assert isinstance(candle, LiveCandleUpdate)
    assert candle.confirm is False
    assert closed_bar(candle) is None


def test_confirmed_kline_is_a_closed_bar() -> None:
    events = parse_bybit_ws_message(
        _kline_payload(confirm=True),
        provider="bybit",
        symbol="BTC/USDT",
        timeframe="4h",
        venue_symbol="BTCUSDT",
    )
    candle = events[0]
    assert isinstance(candle, LiveCandleUpdate)
    bar = closed_bar(candle)
    assert bar is not None
    assert bar.close == Decimal("65100.50")
    assert bar.open_time == datetime(2026, 8, 1, 8, 0, tzinfo=UTC)


def test_missing_confirm_is_treated_as_unconfirmed() -> None:
    payload = json.loads(_kline_payload(confirm=True))
    del payload["data"][0]["confirm"]
    events = parse_bybit_ws_message(
        json.dumps(payload),
        provider="bybit",
        symbol="BTC/USDT",
        timeframe="4h",
        venue_symbol="BTCUSDT",
    )
    candle = events[0]
    assert isinstance(candle, LiveCandleUpdate)
    assert candle.confirm is False
    assert closed_bar(candle) is None


def test_delta_ticker_without_last_price_is_skipped() -> None:
    payload = {
        "topic": "tickers.BTCUSDT",
        "ts": _ts_ms(12),
        "type": "delta",
        "data": {"symbol": "BTCUSDT", "volume24h": "1.00"},
    }
    events = parse_bybit_ws_message(
        json.dumps(payload),
        provider="bybit",
        symbol="BTC/USDT",
        timeframe="4h",
        venue_symbol="BTCUSDT",
    )
    assert events == ()


def test_binary_float_last_price_is_skipped() -> None:
    payload = {
        "topic": "tickers.BTCUSDT",
        "ts": _ts_ms(12),
        "type": "snapshot",
        "data": {"symbol": "BTCUSDT", "lastPrice": 65100.5},
    }
    events = parse_bybit_ws_message(
        json.dumps(payload),
        provider="bybit",
        symbol="BTC/USDT",
        timeframe="4h",
        venue_symbol="BTCUSDT",
    )
    assert events == ()


def test_subscribe_rejection_raises() -> None:
    with pytest.raises(MarketDataStreamError, match="subscribe rejected"):
        parse_bybit_ws_message(
            json.dumps({"op": "subscribe", "success": False, "ret_msg": "error:topic"}),
            provider="bybit",
            symbol="BTC/USDT",
            timeframe="4h",
            venue_symbol="BTCUSDT",
        )


def test_auth_fields_are_rejected() -> None:
    with pytest.raises(MarketDataStreamError, match="auth"):
        parse_bybit_ws_message(
            json.dumps({"topic": "tickers.BTCUSDT", "apiKey": "not-a-real-key", "data": {}}),
            provider="bybit",
            symbol="BTC/USDT",
            timeframe="4h",
            venue_symbol="BTCUSDT",
        )


def test_stream_yields_ticker_and_candles_from_fake_socket() -> None:
    socket = FakeSocket(
        [
            _subscribe_ack(),
            _ticker_payload(),
            _kline_payload(confirm=False),
            _kline_payload(confirm=True),
        ]
    )
    connector = FakeConnector([socket])
    stream, _clock = _stream(connector)
    assert isinstance(stream, LiveMarketDataStream)

    events = asyncio.run(_collect(stream, 3))
    assert isinstance(events[0], LiveTicker)
    assert isinstance(events[1], LiveCandleUpdate)
    assert events[1].confirm is False
    assert isinstance(events[2], LiveCandleUpdate)
    assert events[2].confirm is True
    sent = [json.loads(item) for item in socket.sent]
    assert sent[0] == {
        "op": "subscribe",
        "args": ["kline.240.BTCUSDT", "tickers.BTCUSDT"],
    }
    assert "apiKey" not in sent[0]
    assert connector.urls == ["wss://stream.bybit.com/v5/public/spot"]
    assert socket.closed is True


def test_reconnect_uses_exponential_backoff_then_resubscribes() -> None:
    first = FakeSocket([_subscribe_ack(), ConnectionError("drop")])
    second = FakeSocket([_subscribe_ack(), _ticker_payload()])
    connector = FakeConnector([first, second])
    clock = FakeClock()
    stream = BybitPublicWsStream(
        connector=connector,
        ping_interval_seconds=0,
        rng=lambda: 0.0,
        sleeper=clock.sleep,
        reconnect=ReconnectPolicy(
            initial_backoff_seconds=1.0,
            max_backoff_seconds=8.0,
            jitter_ratio=0.0,
            max_attempts=2,
        ),
    )
    events = asyncio.run(_collect(stream, 1))
    assert isinstance(events[0], LiveTicker)
    assert clock.sleeps == [1.0]
    assert len(connector.urls) == 2
    assert json.loads(second.sent[0])["op"] == "subscribe"
    assert first.closed is True
    assert second.closed is True


def test_reconnect_exhaustion_raises() -> None:
    socket = FakeSocket([_subscribe_ack(), ConnectionError("drop")])
    connector = FakeConnector([socket])
    stream, clock = _stream(
        connector,
        reconnect=ReconnectPolicy(max_attempts=1, jitter_ratio=0.0),
    )

    async def run() -> None:
        async for _event in stream.subscribe("BTC/USDT", "4h"):
            raise AssertionError("no market events expected")

    with pytest.raises(MarketDataStreamDisconnected):
        asyncio.run(run())
    assert clock.sleeps == []


def test_heartbeat_sends_official_ping() -> None:
    socket = FakeSocket([])
    sleeps: list[float] = []

    async def sleeper(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) > 1:
            raise asyncio.CancelledError

    async def run_once() -> None:
        with pytest.raises(asyncio.CancelledError):
            await run_heartbeat(socket, 20.0, sleeper)

    asyncio.run(run_once())
    assert sleeps[0] == 20.0
    assert json.loads(socket.sent[0]) == {"op": "ping"}


def test_confirm_must_be_bool() -> None:
    events = parse_bybit_ws_message(
        _kline_payload(confirm=True),
        provider="bybit",
        symbol="BTC/USDT",
        timeframe="4h",
        venue_symbol="BTCUSDT",
    )
    candle = events[0]
    assert isinstance(candle, LiveCandleUpdate)
    with pytest.raises(TypeError, match="confirm must be bool"):
        LiveCandleUpdate(
            provider=candle.provider,
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            bar=candle.bar,
            confirm="true",  # type: ignore[arg-type]
            event_time=candle.event_time,
        )


def test_parse_rejects_float_construction_via_domain() -> None:
    with pytest.raises(InvalidFinancialValue):
        LiveTicker(
            provider="bybit",
            symbol="BTC/USDT",
            timestamp=datetime(2026, 8, 1, 12, 0, tzinfo=UTC),
            last_price=65100.5,  # type: ignore[arg-type]
        )
