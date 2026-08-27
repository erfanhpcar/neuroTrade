import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pyarrow.parquet as pq
import pytest

from app.domain.errors import InvalidTimestamp
from app.domain.market import OhlcvBar
from app.market_data.base import OhlcvSeries, hash_ohlcv_bars
from app.market_data.errors import (
    CorruptOhlcvDataset,
    EmptyOhlcvDataset,
    ImmutableOhlcvDataset,
    IncompleteOhlcvHistory,
    UnknownOhlcvDataset,
)
from app.market_data.parquet import ParquetOhlcvStore, path_symbol
from app.market_data.replay import load_series_from_json_path

FIXTURE_PATH = Path(__file__).resolve().parents[2] / "replay" / "btc_usdt_4h.json"


def _utc(year: int, month: int, day: int, hour: int) -> datetime:
    return datetime(year, month, day, hour, 0, tzinfo=UTC)


def _bar(open_time: datetime, *, close: str = "65100.50", volume: str = "1.0") -> OhlcvBar:
    open_price = Decimal("65000.10")
    close_price = Decimal(close)
    high = max(open_price, close_price) + Decimal("200")
    low = min(open_price, close_price) - Decimal("100")
    return OhlcvBar(
        open_time=open_time,
        open=open_price,
        high=high,
        low=low,
        close=close_price,
        volume=Decimal(volume),
    )


def _series(bars: tuple[OhlcvBar, ...], *, provider: str = "replay") -> OhlcvSeries:
    return OhlcvSeries.from_bars(
        provider=provider,
        symbol="BTC/USDT",
        timeframe="4h",
        bars=bars,
    )


def test_path_symbol_strips_slash() -> None:
    assert path_symbol("BTC/USDT") == "BTCUSDT"


def test_replay_fixture_round_trip_preserves_bars_and_hash(tmp_path: Path) -> None:
    original = load_series_from_json_path(FIXTURE_PATH)
    store = ParquetOhlcvStore(tmp_path)
    downloaded_at = datetime(2026, 8, 27, 21, 30, tzinfo=UTC)
    manifest = store.write_series(original, downloaded_at=downloaded_at)

    assert manifest.row_count == 6
    assert manifest.dataset_hash == original.dataset_hash
    assert manifest.start == original.bars[0].open_time
    assert manifest.end == original.bars[-1].open_time
    assert manifest.downloaded_at == downloaded_at
    assert len(manifest.files) == 1
    assert manifest.files[0].path == "year=2026/month=08/ohlcv-v1.parquet"

    dataset_dir = store.dataset_dir("replay", "BTC/USDT", "4h")
    assert (dataset_dir / "metadata.json").is_file()
    parquet_path = dataset_dir / manifest.files[0].path
    schema = pq.read_schema(parquet_path)
    for name in ("open", "high", "low", "close", "volume"):
        assert str(schema.field(name).type) == "string"

    loaded = store.read_series("replay", "BTC/USDT", "4h")
    assert loaded.bars == original.bars
    assert loaded.dataset_hash == original.dataset_hash
    assert loaded.dataset_hash == hash_ohlcv_bars(
        provider="replay",
        symbol="BTC/USDT",
        timeframe="4h",
        bars=loaded.bars,
    )


def test_decimal_strings_survive_parquet_without_float(tmp_path: Path) -> None:
    bars = (
        _bar(_utc(2026, 8, 1, 0), close="65000.10", volume="0.1"),
        _bar(_utc(2026, 8, 1, 4), close="65001.25", volume="0.2"),
    )
    series = _series(bars)
    store = ParquetOhlcvStore(tmp_path)
    store.write_series(series, downloaded_at=_utc(2026, 8, 27, 0))
    loaded = store.read_series("replay", "BTC/USDT", "4h")
    assert loaded.bars[0].open == Decimal("65000.10")
    assert loaded.bars[0].volume == Decimal("0.1")
    assert loaded.bars[1].close == Decimal("65001.25")


def test_month_partitions_split_august_and_september(tmp_path: Path) -> None:
    bars = (
        _bar(_utc(2026, 8, 31, 20), close="65010.00"),
        _bar(_utc(2026, 9, 1, 0), close="65020.00"),
    )
    series = _series(bars)
    store = ParquetOhlcvStore(tmp_path)
    manifest = store.write_series(series, downloaded_at=_utc(2026, 8, 27, 0))
    assert [item.path for item in manifest.files] == [
        "year=2026/month=08/ohlcv-v1.parquet",
        "year=2026/month=09/ohlcv-v1.parquet",
    ]
    loaded = store.read_series("replay", "BTC/USDT", "4h")
    assert loaded.bars == bars
    assert loaded.dataset_hash == series.dataset_hash


def test_gapped_series_is_not_written(tmp_path: Path) -> None:
    bars = (
        _bar(_utc(2026, 8, 1, 0)),
        _bar(_utc(2026, 8, 1, 8), close="65410.00"),
    )
    store = ParquetOhlcvStore(tmp_path)
    with pytest.raises(IncompleteOhlcvHistory, match="not contiguous"):
        store.write_series(_series(bars), downloaded_at=_utc(2026, 8, 27, 0))
    assert list(tmp_path.iterdir()) == []


def test_empty_series_is_not_written(tmp_path: Path) -> None:
    series = OhlcvSeries.from_bars(
        provider="replay",
        symbol="BTC/USDT",
        timeframe="4h",
        bars=(),
    )
    store = ParquetOhlcvStore(tmp_path)
    with pytest.raises(EmptyOhlcvDataset, match="empty"):
        store.write_series(series, downloaded_at=_utc(2026, 8, 27, 0))


def test_naive_downloaded_at_is_rejected(tmp_path: Path) -> None:
    bars = (_bar(_utc(2026, 8, 1, 0)),)
    store = ParquetOhlcvStore(tmp_path)
    with pytest.raises(InvalidTimestamp, match="timezone-aware"):
        store.write_series(
            _series(bars),
            downloaded_at=datetime(2026, 8, 27, 0, 0),
        )


def test_identical_rewrite_is_idempotent(tmp_path: Path) -> None:
    bars = (_bar(_utc(2026, 8, 1, 0)), _bar(_utc(2026, 8, 1, 4), close="65020.00"))
    series = _series(bars)
    store = ParquetOhlcvStore(tmp_path)
    first = store.write_series(series, downloaded_at=_utc(2026, 8, 27, 1))
    second = store.write_series(series, downloaded_at=_utc(2026, 8, 27, 2))
    assert first.dataset_hash == second.dataset_hash
    assert second.downloaded_at == first.downloaded_at
    assert second.downloaded_at == _utc(2026, 8, 27, 1)


def test_conflicting_overwrite_is_rejected(tmp_path: Path) -> None:
    first_bars = (_bar(_utc(2026, 8, 1, 0)),)
    second_bars = (_bar(_utc(2026, 8, 1, 0), close="66000.00"),)
    store = ParquetOhlcvStore(tmp_path)
    store.write_series(_series(first_bars), downloaded_at=_utc(2026, 8, 27, 0))
    with pytest.raises(ImmutableOhlcvDataset, match="already exists"):
        store.write_series(_series(second_bars), downloaded_at=_utc(2026, 8, 27, 1))
    loaded = store.read_series("replay", "BTC/USDT", "4h")
    assert loaded.bars[0].close == Decimal("65100.50")


def test_tampered_parquet_bytes_are_detected(tmp_path: Path) -> None:
    bars = (_bar(_utc(2026, 8, 1, 0)),)
    store = ParquetOhlcvStore(tmp_path)
    manifest = store.write_series(_series(bars), downloaded_at=_utc(2026, 8, 27, 0))
    parquet_path = store.dataset_dir("replay", "BTC/USDT", "4h") / manifest.files[0].path
    parquet_path.write_bytes(parquet_path.read_bytes() + b"tamper")
    with pytest.raises(CorruptOhlcvDataset, match="sha256"):
        store.read_series("replay", "BTC/USDT", "4h")


def test_missing_dataset_raises(tmp_path: Path) -> None:
    store = ParquetOhlcvStore(tmp_path)
    with pytest.raises(UnknownOhlcvDataset, match="no parquet dataset"):
        store.read_series("replay", "BTC/USDT", "4h")


def test_metadata_checksum_mismatch_is_detected(tmp_path: Path) -> None:
    bars = (_bar(_utc(2026, 8, 1, 0)),)
    store = ParquetOhlcvStore(tmp_path)
    store.write_series(_series(bars), downloaded_at=_utc(2026, 8, 27, 0))
    meta_path = store.dataset_dir("replay", "BTC/USDT", "4h") / "metadata.json"
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    payload["dataset_hash"] = "0" * 64
    meta_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(CorruptOhlcvDataset, match="dataset_hash"):
        store.read_series("replay", "BTC/USDT", "4h")
