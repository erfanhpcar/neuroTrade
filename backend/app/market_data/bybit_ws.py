"""Bybit public WebSocket ticker/kline adapter.

Uses official public streams only:

- ``wss://stream.bybit.com/v5/public/spot`` (default category, matches REST)
- ``wss://stream.bybit.com/v5/public/linear``
- ``wss://stream.bybit.com/v5/public/inverse``

Subscribe: ``tickers.{symbol}`` and ``kline.{interval}.{symbol}``.
Heartbeat: ``{"op": "ping"}`` every 20 seconds (official recommendation).
No API keys, no CCXT, no private topics.

Docs:
https://bybit-exchange.github.io/docs/v5/ws/connect
https://bybit-exchange.github.io/docs/v5/websocket/public/kline
https://bybit-exchange.github.io/docs/v5/websocket/public/ticker
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from datetime import UTC, datetime
from typing import Final, Protocol

from websockets.asyncio.client import connect as websockets_connect
from websockets.exceptions import ConnectionClosed, WebSocketException

from app.domain.fields import require_symbol, require_timeframe
from app.domain.market import OhlcvBar
from app.domain.money import require_non_negative_decimal, require_positive_decimal
from app.market_data.bybit import to_bybit_category, to_bybit_interval, to_bybit_symbol
from app.market_data.errors import (
    MarketDataError,
    MarketDataStreamDisconnected,
    MarketDataStreamError,
)
from app.market_data.rate_limit import AsyncSleeper, UnitIntervalRng, default_rng
from app.market_data.reconnect import (
    DEFAULT_WS_RECONNECT,
    ReconnectPolicy,
    reconnect_backoff_seconds,
)
from app.market_data.stream import LiveCandleUpdate, LiveMarketEvent, LiveTicker

logger = logging.getLogger("neurotrade.market_data.bybit_ws")

BYBIT_DEFAULT_WS_BASE_URL: Final = "wss://stream.bybit.com"
BYBIT_PUBLIC_WS_PATHS: Final[dict[str, str]] = {
    "spot": "/v5/public/spot",
    "linear": "/v5/public/linear",
    "inverse": "/v5/public/inverse",
}
BYBIT_DEFAULT_PING_INTERVAL_SECONDS: Final = 20.0

_AUTH_FIELD_NAMES: Final = frozenset(
    {
        "api_key",
        "apiKey",
        "secret",
        "sign",
        "signature",
        "token",
        "authorization",
    }
)

_DISCONNECT_ERRORS: Final = (ConnectionError, TimeoutError, OSError, EOFError)


class PublicTextSocket(Protocol):
    """Minimal text WebSocket used by the Bybit public stream."""

    async def send(self, message: str) -> None:
        """Send one text frame."""

    async def recv(self) -> str:
        """Receive one text frame. Connection loss should raise ``ConnectionError``."""

    async def close(self) -> None:
        """Close the socket. Idempotent."""


WebSocketConnector = Callable[[str], Awaitable[PublicTextSocket]]


class _ClientConnection(Protocol):
    async def send(self, message: str) -> None: ...

    async def recv(self) -> str | bytes: ...

    async def close(self) -> None: ...


class _WebsocketsTextSocket:
    """Adapter over the ``websockets`` client. Used only at the network boundary."""

    def __init__(self, connection: _ClientConnection) -> None:
        self._connection = connection

    async def send(self, message: str) -> None:
        await self._connection.send(message)

    async def recv(self) -> str:
        try:
            raw = await self._connection.recv()
        except (ConnectionClosed, WebSocketException, TimeoutError, OSError) as exc:
            raise ConnectionError("Bybit public WebSocket recv failed") from exc
        if isinstance(raw, bytes):
            return raw.decode("utf-8")
        if isinstance(raw, str):
            return raw
        raise MarketDataStreamError(f"WebSocket frame must be text, got {type(raw).__name__}")

    async def close(self) -> None:
        await self._connection.close()


async def connect_bybit_public_ws(url: str) -> PublicTextSocket:
    """Open a public Bybit WebSocket. Callers own close(). Never attach API keys."""

    if not url.startswith("wss://"):
        raise MarketDataStreamError("Bybit public WebSocket URL must use wss://")
    connection = await websockets_connect(url, open_timeout=10, max_size=2**20)
    return _WebsocketsTextSocket(connection)


def bybit_public_ws_url(category: str, *, base_url: str = BYBIT_DEFAULT_WS_BASE_URL) -> str:
    mapped = to_bybit_category(category)
    return f"{base_url.rstrip('/')}{BYBIT_PUBLIC_WS_PATHS[mapped]}"


class BybitPublicWsStream:
    """``LiveMarketDataStream`` over Bybit public ticker + kline topics."""

    def __init__(
        self,
        *,
        connector: WebSocketConnector | None = None,
        category: str = "spot",
        ws_base_url: str = BYBIT_DEFAULT_WS_BASE_URL,
        reconnect: ReconnectPolicy | None = None,
        ping_interval_seconds: float = BYBIT_DEFAULT_PING_INTERVAL_SECONDS,
        rng: UnitIntervalRng | None = None,
        sleeper: AsyncSleeper | None = None,
    ) -> None:
        if ping_interval_seconds < 0:
            raise MarketDataError("ping_interval_seconds must be >= 0")
        self._connector: WebSocketConnector = connector or connect_bybit_public_ws
        self._category = to_bybit_category(category)
        self._ws_base_url = ws_base_url.rstrip("/")
        self._reconnect = reconnect or DEFAULT_WS_RECONNECT
        self._ping_interval_seconds = ping_interval_seconds
        self._rng: UnitIntervalRng = rng or default_rng()
        self._sleeper: AsyncSleeper = sleeper or _asyncio_sleep
        self._stopping = False

    @property
    def name(self) -> str:
        return "bybit"

    @property
    def category(self) -> str:
        return self._category

    def url(self) -> str:
        return bybit_public_ws_url(self._category, base_url=self._ws_base_url)

    async def aclose(self) -> None:
        """Stop reconnecting after the current socket is closed."""

        self._stopping = True

    async def subscribe(
        self,
        symbol: str,
        timeframe: str,
    ) -> AsyncIterator[LiveMarketEvent]:
        canonical_symbol = require_symbol(symbol)
        canonical_timeframe = require_timeframe(timeframe)
        venue_symbol = to_bybit_symbol(canonical_symbol)
        interval = to_bybit_interval(canonical_timeframe)
        topics = (
            f"kline.{interval}.{venue_symbol}",
            f"tickers.{venue_symbol}",
        )
        url = self.url()
        session_index = 0
        reconnect_attempt = 0
        while not self._stopping:
            if (
                self._reconnect.max_attempts is not None
                and session_index >= self._reconnect.max_attempts
            ):
                raise MarketDataStreamDisconnected(
                    f"Bybit public WebSocket reconnect exhausted after "
                    f"{self._reconnect.max_attempts} attempt(s)"
                )
            session_index += 1
            try:
                async for event in self._run_session(
                    url=url,
                    topics=topics,
                    symbol=canonical_symbol,
                    timeframe=canonical_timeframe,
                    venue_symbol=venue_symbol,
                ):
                    reconnect_attempt = 0
                    yield event
            except GeneratorExit:
                self._stopping = True
                raise
            except MarketDataStreamError:
                raise
            except _DISCONNECT_ERRORS as exc:
                logger.warning(
                    "bybit public ws disconnected url_host=%s session=%s",
                    _url_host(url),
                    session_index,
                )
                last_disconnect: BaseException = exc
            else:
                last_disconnect = ConnectionError("Bybit public WebSocket session ended")
            if self._stopping:
                return
            if (
                self._reconnect.max_attempts is not None
                and session_index >= self._reconnect.max_attempts
            ):
                raise MarketDataStreamDisconnected(
                    f"Bybit public WebSocket reconnect exhausted after "
                    f"{self._reconnect.max_attempts} attempt(s)"
                ) from last_disconnect
            delay = reconnect_backoff_seconds(reconnect_attempt, self._reconnect, self._rng)
            reconnect_attempt += 1
            await self._sleeper(delay)

    async def _run_session(
        self,
        *,
        url: str,
        topics: tuple[str, ...],
        symbol: str,
        timeframe: str,
        venue_symbol: str,
    ) -> AsyncIterator[LiveMarketEvent]:
        socket = await self._connector(url)
        ping_task: asyncio.Task[None] | None = None
        try:
            await _send_json(socket, {"op": "subscribe", "args": list(topics)})
            if self._ping_interval_seconds > 0:
                ping_task = _schedule_heartbeat(socket, self._ping_interval_seconds, self._sleeper)
            while not self._stopping:
                raw = await socket.recv()
                for event in parse_bybit_ws_message(
                    raw,
                    provider=self.name,
                    symbol=symbol,
                    timeframe=timeframe,
                    venue_symbol=venue_symbol,
                ):
                    yield event
        finally:
            if ping_task is not None:
                ping_task.cancel()
                try:
                    await ping_task
                except asyncio.CancelledError:
                    pass
            await socket.close()


async def run_heartbeat(
    socket: PublicTextSocket,
    interval_seconds: float,
    sleeper: AsyncSleeper,
) -> None:
    """Send official ``{"op": "ping"}`` frames until cancelled."""

    while True:
        await sleeper(interval_seconds)
        await _send_json(socket, {"op": "ping"})


def parse_bybit_ws_message(
    raw: object,
    *,
    provider: str,
    symbol: str,
    timeframe: str,
    venue_symbol: str,
) -> tuple[LiveMarketEvent, ...]:
    """Parse one public WS payload. Control frames yield an empty tuple.

    A subscribe rejection raises. Malformed market payloads are skipped after
    a warning so one bad frame cannot tear down the reconnect loop.
    """

    try:
        payload = _as_object(raw)
    except MarketDataError:
        logger.warning("bybit public ws skipped non-object payload")
        return ()
    _assert_no_auth_fields(payload)
    op = payload.get("op")
    if op == "subscribe":
        success = payload.get("success")
        if success is False:
            ret_msg = payload.get("ret_msg", "")
            raise MarketDataStreamError(f"Bybit public WS subscribe rejected: {ret_msg!r}")
        return ()
    if op in {"ping", "pong"}:
        return ()
    topic = payload.get("topic")
    if not isinstance(topic, str) or not topic:
        return ()
    try:
        if topic.startswith("tickers."):
            event = _parse_ticker(
                payload,
                provider=provider,
                symbol=symbol,
                venue_symbol=venue_symbol,
                topic=topic,
            )
            return (event,) if event is not None else ()
        if topic.startswith("kline."):
            return _parse_kline(
                payload,
                provider=provider,
                symbol=symbol,
                timeframe=timeframe,
                venue_symbol=venue_symbol,
                topic=topic,
            )
    except (MarketDataError, TypeError, ValueError) as exc:
        logger.warning(
            "bybit public ws skipped malformed payload topic=%s err=%s",
            topic,
            type(exc).__name__,
        )
        return ()
    logger.warning("bybit public ws ignored unknown topic=%s", topic)
    return ()


def _parse_ticker(
    payload: dict[str, object],
    *,
    provider: str,
    symbol: str,
    venue_symbol: str,
    topic: str,
) -> LiveTicker | None:
    expected = f"tickers.{venue_symbol}"
    if topic != expected:
        raise MarketDataError(f"ticker topic {topic!r} does not match {expected!r}")
    data = payload.get("data")
    if isinstance(data, list):
        if not data:
            return None
        data = data[0]
    if not isinstance(data, dict):
        raise MarketDataError("ticker data must be an object")
    last_price = data.get("lastPrice")
    msg_type = payload.get("type")
    if last_price in (None, ""):
        if msg_type == "delta":
            return None
        raise MarketDataError("ticker snapshot is missing lastPrice")
    return LiveTicker(
        provider=provider,
        symbol=symbol,
        timestamp=_from_millis(payload.get("ts"), field="ts"),
        last_price=require_positive_decimal(last_price, field="lastPrice"),
    )


def _parse_kline(
    payload: dict[str, object],
    *,
    provider: str,
    symbol: str,
    timeframe: str,
    venue_symbol: str,
    topic: str,
) -> tuple[LiveCandleUpdate, ...]:
    interval = to_bybit_interval(timeframe)
    expected = f"kline.{interval}.{venue_symbol}"
    if topic != expected:
        raise MarketDataError(f"kline topic {topic!r} does not match {expected!r}")
    data = payload.get("data")
    if isinstance(data, dict):
        rows: list[object] = [data]
    elif isinstance(data, list):
        rows = data
    else:
        raise MarketDataError("kline data must be an object or array")
    event_time = _from_millis(payload.get("ts"), field="ts")
    updates: list[LiveCandleUpdate] = []
    for row in rows:
        if not isinstance(row, dict):
            raise MarketDataError("kline row must be an object")
        confirm = row.get("confirm") is True
        row_time = row.get("timestamp")
        update_time = (
            _from_millis(row_time, field="timestamp") if row_time is not None else event_time
        )
        updates.append(
            LiveCandleUpdate(
                provider=provider,
                symbol=symbol,
                timeframe=timeframe,
                bar=OhlcvBar(
                    open_time=_from_millis(row.get("start"), field="start"),
                    open=require_positive_decimal(row.get("open"), field="open"),
                    high=require_positive_decimal(row.get("high"), field="high"),
                    low=require_positive_decimal(row.get("low"), field="low"),
                    close=require_positive_decimal(row.get("close"), field="close"),
                    volume=require_non_negative_decimal(row.get("volume"), field="volume"),
                ),
                confirm=confirm,
                event_time=update_time,
            )
        )
    return tuple(updates)


def _as_object(raw: object) -> dict[str, object]:
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    if isinstance(raw, str):
        try:
            parsed: object = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MarketDataError("WebSocket payload is not JSON") from exc
        raw = parsed
    if not isinstance(raw, dict):
        raise MarketDataError("WebSocket payload must be an object")
    return raw


def _from_millis(value: object, *, field: str) -> datetime:
    if isinstance(value, bool) or value is None:
        raise MarketDataError(f"{field} must be millisecond epoch")
    if isinstance(value, int):
        millis = value
    elif isinstance(value, str):
        text = value.strip()
        if not text.isdigit():
            raise MarketDataError(f"{field} is not millisecond epoch: {value!r}")
        millis = int(text)
    else:
        raise MarketDataError(f"{field} must be str or int, got {type(value).__name__}")
    if millis < 0:
        raise MarketDataError(f"{field} must be >= 0")
    return datetime.fromtimestamp(millis / 1000, tz=UTC)


def _assert_no_auth_fields(payload: Mapping[str, object]) -> None:
    for name in payload:
        if name in _AUTH_FIELD_NAMES or name.lower() in {
            item.lower() for item in _AUTH_FIELD_NAMES
        }:
            raise MarketDataStreamError("Bybit public WS payload must not include auth fields")


async def _send_json(socket: PublicTextSocket, payload: Mapping[str, object]) -> None:
    _assert_no_auth_fields(payload)
    await socket.send(json.dumps(dict(payload), separators=(",", ":")))


def _schedule_heartbeat(
    socket: PublicTextSocket,
    interval_seconds: float,
    sleeper: AsyncSleeper,
) -> asyncio.Task[None]:
    return asyncio.create_task(run_heartbeat(socket, interval_seconds, sleeper))


def _url_host(url: str) -> str:
    without_scheme = url.split("://", 1)[-1]
    return without_scheme.split("/", 1)[0]


async def _asyncio_sleep(seconds: float) -> None:
    await asyncio.sleep(seconds)
