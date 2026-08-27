"""Immutable Parquet store for contiguous historical OHLCV datasets.

Layout matches ``docs/04_DATA_SCHEMAS.md``:

```text
<root>/
  provider=<provider>/
    symbol=<BTCUSDT>/
      timeframe=<4h>/
        metadata.json
        year=YYYY/month=MM/ohlcv-v1.parquet
```

Prices and volume are stored as canonical decimal strings, never binary floats.
``require_contiguous_ohlcv`` runs before every write. ``downloaded_at`` is injected;
this module does not read the wall clock. Generated files under
``backend/data/market/`` stay gitignored.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from itertools import groupby
from pathlib import Path
from uuid import uuid4

import pyarrow as pa
import pyarrow.parquet as pq

from app.domain.fields import require_symbol, require_text, require_timeframe
from app.domain.market import OhlcvBar
from app.domain.money import decimal_to_text
from app.domain.timestamps import require_utc
from app.market_data.base import OHLCV_SCHEMA_VERSION, OhlcvSeries, hash_ohlcv_bars
from app.market_data.errors import (
    CorruptOhlcvDataset,
    EmptyOhlcvDataset,
    ImmutableOhlcvDataset,
    MarketDataError,
    UnknownOhlcvDataset,
)
from app.market_data.integrity import require_contiguous_ohlcv

PARQUET_FILE_NAME = "ohlcv-v1.parquet"
METADATA_FILE_NAME = "metadata.json"
_OHLCV_COLUMNS = ("open_time", "open", "high", "low", "close", "volume")
_PARQUET_SCHEMA = pa.schema(
    [
        pa.field("open_time", pa.timestamp("us", tz="UTC")),
        pa.field("open", pa.string()),
        pa.field("high", pa.string()),
        pa.field("low", pa.string()),
        pa.field("close", pa.string()),
        pa.field("volume", pa.string()),
    ]
)


def path_symbol(symbol: str) -> str:
    """Return the hive-partition symbol token (``BTC/USDT`` → ``BTCUSDT``)."""

    compact = "".join(ch for ch in require_symbol(symbol) if ch.isalnum())
    if not compact:
        raise MarketDataError("symbol has no alphanumeric characters for a dataset path")
    return compact


def _path_component(value: str, *, field: str) -> str:
    text = require_text(value, field=field)
    if "/" in text or "\\" in text or text in {".", ".."}:
        raise MarketDataError(f"{field} is not a safe dataset path component: {text!r}")
    return text


def dataset_relative_dir(*, provider: str, symbol: str, timeframe: str) -> Path:
    """Return the hive path under the store root for one series."""

    return Path(
        f"provider={_path_component(provider, field='provider')}",
        f"symbol={path_symbol(symbol)}",
        f"timeframe={_path_component(require_timeframe(timeframe), field='timeframe')}",
    )


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file's bytes."""

    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _month_partition(open_time: datetime) -> tuple[int, int]:
    utc_time = require_utc(open_time, field="open_time")
    return utc_time.year, utc_time.month


def _partition_relative_path(year: int, month: int) -> str:
    return f"year={year:04d}/month={month:02d}/{PARQUET_FILE_NAME}"


@dataclass(frozen=True)
class OhlcvParquetFile:
    """One month partition file recorded in dataset metadata."""

    path: str
    row_count: int
    sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", require_text(self.path, field="path"))
        if self.row_count < 1:
            raise MarketDataError("parquet file row_count must be >= 1")
        object.__setattr__(self, "sha256", require_text(self.sha256, field="sha256"))
        if Path(self.path).is_absolute() or ".." in Path(self.path).parts:
            raise MarketDataError(f"parquet file path must stay inside the dataset: {self.path}")


@dataclass(frozen=True)
class OhlcvDatasetManifest:
    """Sidecar identity for one immutable OHLCV dataset."""

    schema_version: str
    provider: str
    symbol: str
    timeframe: str
    start: datetime
    end: datetime
    downloaded_at: datetime
    row_count: int
    dataset_hash: str
    files: tuple[OhlcvParquetFile, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "schema_version", require_text(self.schema_version, field="schema_version")
        )
        object.__setattr__(self, "provider", require_text(self.provider, field="provider"))
        object.__setattr__(self, "symbol", require_symbol(self.symbol))
        object.__setattr__(self, "timeframe", require_timeframe(self.timeframe))
        object.__setattr__(self, "start", require_utc(self.start, field="start"))
        object.__setattr__(self, "end", require_utc(self.end, field="end"))
        object.__setattr__(
            self, "downloaded_at", require_utc(self.downloaded_at, field="downloaded_at")
        )
        object.__setattr__(
            self, "dataset_hash", require_text(self.dataset_hash, field="dataset_hash")
        )
        if self.row_count < 1:
            raise MarketDataError("dataset row_count must be >= 1")
        if not self.files:
            raise MarketDataError("dataset manifest must list at least one parquet file")
        if self.end < self.start:
            raise MarketDataError("dataset end is before start")
        object.__setattr__(self, "files", tuple(self.files))

    def to_json_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "provider": self.provider,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "downloaded_at": self.downloaded_at.isoformat(),
            "row_count": self.row_count,
            "dataset_hash": self.dataset_hash,
            "files": [
                {"path": item.path, "row_count": item.row_count, "sha256": item.sha256}
                for item in self.files
            ],
        }


def _parse_utc(value: object, *, field: str) -> datetime:
    if not isinstance(value, str):
        raise CorruptOhlcvDataset(f"manifest {field} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CorruptOhlcvDataset(f"manifest {field} is not ISO-8601: {value!r}") from exc
    return require_utc(parsed, field=field)


def manifest_from_json(payload: object) -> OhlcvDatasetManifest:
    """Parse and validate ``metadata.json``."""

    if not isinstance(payload, dict):
        raise CorruptOhlcvDataset("dataset metadata must be a JSON object")
    required = {
        "schema_version",
        "provider",
        "symbol",
        "timeframe",
        "start",
        "end",
        "downloaded_at",
        "row_count",
        "dataset_hash",
        "files",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise CorruptOhlcvDataset(f"dataset metadata is missing fields: {', '.join(missing)}")
    unexpected = sorted(set(payload) - required)
    if unexpected:
        raise CorruptOhlcvDataset(
            f"dataset metadata has unexpected fields: {', '.join(unexpected)}"
        )
    files_raw = payload["files"]
    if not isinstance(files_raw, list) or not files_raw:
        raise CorruptOhlcvDataset("dataset metadata files must be a non-empty list")
    files: list[OhlcvParquetFile] = []
    for item in files_raw:
        if not isinstance(item, dict):
            raise CorruptOhlcvDataset("dataset metadata file entry must be an object")
        file_required = {"path", "row_count", "sha256"}
        file_missing = sorted(file_required - set(item))
        if file_missing:
            raise CorruptOhlcvDataset(
                f"dataset metadata file entry is missing fields: {', '.join(file_missing)}"
            )
        if sorted(set(item) - file_required):
            raise CorruptOhlcvDataset("dataset metadata file entry has unexpected fields")
        row_count = item["row_count"]
        if not isinstance(row_count, int) or isinstance(row_count, bool):
            raise CorruptOhlcvDataset("dataset metadata file row_count must be an int")
        path = item["path"]
        sha256 = item["sha256"]
        if not isinstance(path, str) or not isinstance(sha256, str):
            raise CorruptOhlcvDataset("dataset metadata file path and sha256 must be strings")
        files.append(OhlcvParquetFile(path=path, row_count=row_count, sha256=sha256))
    row_count = payload["row_count"]
    if not isinstance(row_count, int) or isinstance(row_count, bool):
        raise CorruptOhlcvDataset("dataset metadata row_count must be an int")
    schema_version = payload["schema_version"]
    provider = payload["provider"]
    symbol = payload["symbol"]
    timeframe = payload["timeframe"]
    dataset_hash = payload["dataset_hash"]
    if not isinstance(schema_version, str):
        raise CorruptOhlcvDataset("dataset metadata schema_version must be a string")
    if not isinstance(provider, str):
        raise CorruptOhlcvDataset("dataset metadata provider must be a string")
    if not isinstance(symbol, str):
        raise CorruptOhlcvDataset("dataset metadata symbol must be a string")
    if not isinstance(timeframe, str):
        raise CorruptOhlcvDataset("dataset metadata timeframe must be a string")
    if not isinstance(dataset_hash, str):
        raise CorruptOhlcvDataset("dataset metadata dataset_hash must be a string")
    return OhlcvDatasetManifest(
        schema_version=schema_version,
        provider=provider,
        symbol=symbol,
        timeframe=timeframe,
        start=_parse_utc(payload["start"], field="start"),
        end=_parse_utc(payload["end"], field="end"),
        downloaded_at=_parse_utc(payload["downloaded_at"], field="downloaded_at"),
        row_count=row_count,
        dataset_hash=dataset_hash,
        files=tuple(files),
    )


def _write_parquet(path: Path, bars: Sequence[OhlcvBar]) -> None:
    table = pa.table(
        {
            "open_time": [bar.open_time for bar in bars],
            "open": [decimal_to_text(bar.open) for bar in bars],
            "high": [decimal_to_text(bar.high) for bar in bars],
            "low": [decimal_to_text(bar.low) for bar in bars],
            "close": [decimal_to_text(bar.close) for bar in bars],
            "volume": [decimal_to_text(bar.volume) for bar in bars],
        },
        schema=_PARQUET_SCHEMA,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path, compression="zstd", use_dictionary=False)


def _read_parquet_bars(path: Path) -> tuple[OhlcvBar, ...]:
    # Read the file itself. ``pq.read_table(path)`` in PyArrow 22 infers hive
    # columns from parent directories (provider/symbol/year/month), which are
    # not stored in the file and must not enter the OHLCV schema.
    table = pq.ParquetFile(path).read()
    if tuple(table.column_names) != _OHLCV_COLUMNS:
        raise CorruptOhlcvDataset(
            f"parquet columns {list(table.column_names)} do not match {_OHLCV_COLUMNS}"
        )
    for name in ("open", "high", "low", "close", "volume"):
        if not pa.types.is_string(table.schema.field(name).type):
            raise CorruptOhlcvDataset(f"parquet column {name} must be string, not float")
    rows = table.to_pydict()
    bars: list[OhlcvBar] = []
    count = len(rows["open_time"])
    for index in range(count):
        open_time = rows["open_time"][index]
        if not isinstance(open_time, datetime):
            raise CorruptOhlcvDataset("parquet open_time must decode to datetime")
        if open_time.tzinfo is None:
            raise CorruptOhlcvDataset("parquet open_time must be timezone-aware UTC")
        bars.append(
            OhlcvBar(
                open_time=require_utc(open_time, field="open_time"),
                open=rows["open"][index],
                high=rows["high"][index],
                low=rows["low"][index],
                close=rows["close"][index],
                volume=rows["volume"][index],
            )
        )
    return tuple(bars)


class ParquetOhlcvStore:
    """Filesystem store for versioned historical OHLCV Parquet datasets."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        return self._root

    def dataset_dir(self, provider: str, symbol: str, timeframe: str) -> Path:
        return self._root / dataset_relative_dir(
            provider=provider, symbol=symbol, timeframe=timeframe
        )

    def write_series(
        self,
        series: OhlcvSeries,
        *,
        downloaded_at: datetime,
    ) -> OhlcvDatasetManifest:
        """Persist a contiguous series. Identical rewrites are idempotent."""

        downloaded_at = require_utc(downloaded_at, field="downloaded_at")
        series = require_contiguous_ohlcv(series)
        if not series.bars:
            raise EmptyOhlcvDataset(
                f"refusing empty OHLCV dataset for {series.symbol} {series.timeframe}"
            )

        destination = self.dataset_dir(series.provider, series.symbol, series.timeframe)
        existing_meta = destination / METADATA_FILE_NAME
        if existing_meta.is_file():
            existing = self.read_manifest(series.provider, series.symbol, series.timeframe)
            if existing.dataset_hash != series.dataset_hash:
                raise ImmutableOhlcvDataset(
                    f"dataset {series.symbol} {series.timeframe} already exists with hash "
                    f"{existing.dataset_hash}; new hash {series.dataset_hash}"
                )
            loaded = self.read_series(series.provider, series.symbol, series.timeframe)
            if loaded.bars != series.bars:
                raise CorruptOhlcvDataset("existing dataset hash matched but bar contents differ")
            return existing

        staging = destination.parent / f".{destination.name}.tmp-{uuid4().hex}"
        try:
            files = self._write_partitions(staging, series.bars)
            manifest = OhlcvDatasetManifest(
                schema_version=OHLCV_SCHEMA_VERSION,
                provider=series.provider,
                symbol=series.symbol,
                timeframe=series.timeframe,
                start=series.bars[0].open_time,
                end=series.bars[-1].open_time,
                downloaded_at=downloaded_at,
                row_count=len(series.bars),
                dataset_hash=series.dataset_hash,
                files=files,
            )
            metadata_path = staging / METADATA_FILE_NAME
            metadata_path.write_text(
                json.dumps(manifest.to_json_dict(), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            destination.parent.mkdir(parents=True, exist_ok=True)
            staging.rename(destination)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return manifest

    def read_manifest(self, provider: str, symbol: str, timeframe: str) -> OhlcvDatasetManifest:
        path = self.dataset_dir(provider, symbol, timeframe) / METADATA_FILE_NAME
        if not path.is_file():
            raise UnknownOhlcvDataset(f"no parquet dataset for {provider} {symbol} {timeframe}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CorruptOhlcvDataset("dataset metadata.json is not valid JSON") from exc
        return manifest_from_json(payload)

    def read_series(self, provider: str, symbol: str, timeframe: str) -> OhlcvSeries:
        """Load bars, verify per-file SHA-256, and recompute ``dataset_hash``."""

        manifest = self.read_manifest(provider, symbol, timeframe)
        if (
            manifest.provider != provider
            or manifest.symbol != symbol
            or manifest.timeframe != timeframe
        ):
            raise CorruptOhlcvDataset("dataset metadata identity does not match the request")
        dataset_dir = self.dataset_dir(provider, symbol, timeframe)
        bars: list[OhlcvBar] = []
        for item in manifest.files:
            path = dataset_dir / item.path
            if not path.is_file():
                raise CorruptOhlcvDataset(f"missing parquet partition {item.path}")
            digest = sha256_file(path)
            if digest != item.sha256:
                raise CorruptOhlcvDataset(
                    f"parquet partition {item.path} sha256 {digest} != {item.sha256}"
                )
            partition_bars = _read_parquet_bars(path)
            if len(partition_bars) != item.row_count:
                raise CorruptOhlcvDataset(
                    f"parquet partition {item.path} row_count "
                    f"{len(partition_bars)} != {item.row_count}"
                )
            bars.extend(partition_bars)
        if len(bars) != manifest.row_count:
            raise CorruptOhlcvDataset(
                f"dataset row_count {len(bars)} != metadata {manifest.row_count}"
            )
        recomputed = hash_ohlcv_bars(
            provider=manifest.provider,
            symbol=manifest.symbol,
            timeframe=manifest.timeframe,
            bars=bars,
            schema_version=manifest.schema_version,
        )
        if recomputed != manifest.dataset_hash:
            raise CorruptOhlcvDataset(
                f"recomputed dataset_hash {recomputed} != metadata {manifest.dataset_hash}"
            )
        series = OhlcvSeries.from_bars(
            provider=manifest.provider,
            symbol=manifest.symbol,
            timeframe=manifest.timeframe,
            bars=bars,
            dataset_hash=manifest.dataset_hash,
        )
        require_contiguous_ohlcv(series)
        return series

    def _write_partitions(
        self, staging: Path, bars: tuple[OhlcvBar, ...]
    ) -> tuple[OhlcvParquetFile, ...]:
        files: list[OhlcvParquetFile] = []
        for (year, month), grouped in groupby(
            bars, key=lambda bar: _month_partition(bar.open_time)
        ):
            month_bars = tuple(grouped)
            relative = _partition_relative_path(year, month)
            path = staging / relative
            _write_parquet(path, month_bars)
            files.append(
                OhlcvParquetFile(
                    path=relative,
                    row_count=len(month_bars),
                    sha256=sha256_file(path),
                )
            )
        return tuple(files)
