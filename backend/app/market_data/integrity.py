"""Detect missing candles and off-grid / out-of-order OHLCV bars.

``normalize_bars`` still sorts and collapses identical duplicates. This module
is the detector so gaps and irregular timestamps are not silently ignored.
Historical REST adapters may collect pages newest-first; that is not treated as
a data defect. After sort, bars must sit on a regular timeframe grid.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.market import OhlcvBar
from app.market_data.base import OhlcvSeries, normalize_bars
from app.market_data.errors import IncompleteOhlcvHistory
from app.market_data.timeframe import (
    timeframe_duration,
    timeframe_duration_seconds,
    uses_epoch_alignment,
)

logger = logging.getLogger("neurotrade.market_data.integrity")

DEFAULT_MAX_REPORTED_TIMESTAMPS = 1024


def _input_was_unordered(bars: Sequence[OhlcvBar]) -> bool:
    previous: datetime | None = None
    for bar in bars:
        if previous is not None and bar.open_time < previous:
            return True
        previous = bar.open_time
    return False


def _is_epoch_aligned(open_time: datetime, duration_seconds: int) -> bool:
    return int(open_time.timestamp()) % duration_seconds == 0


@dataclass(frozen=True)
class OhlcvIntegrityReport:
    """Quality report for one symbol/timeframe window.

    ``missing_open_times`` are expected grid times between the first and last
    bar that are absent. ``unexpected_open_times`` are present bars that are not
    on that first-bar grid (including intra-interval timestamps).
    ``epoch_misaligned_open_times`` are bars whose Unix timestamp is not a
    multiple of the timeframe; unused for ``1w``.
    """

    timeframe: str
    bar_count: int
    missing_open_times: tuple[datetime, ...]
    unexpected_open_times: tuple[datetime, ...]
    epoch_misaligned_open_times: tuple[datetime, ...]
    missing_count: int
    unexpected_count: int
    truncated: bool
    input_was_unordered: bool

    @property
    def is_contiguous(self) -> bool:
        return self.missing_count == 0 and self.unexpected_count == 0

    @property
    def is_epoch_aligned(self) -> bool:
        return not self.epoch_misaligned_open_times

    @property
    def has_issues(self) -> bool:
        """True when bars are gapped, off-grid, or epoch-misaligned.

        Unordered raw input is reported separately; REST pagination newest-first
        is expected and is not an integrity failure.
        """

        return not self.is_contiguous or not self.is_epoch_aligned


def inspect_ohlcv(
    bars: Sequence[OhlcvBar],
    timeframe: str,
    *,
    max_reported: int = DEFAULT_MAX_REPORTED_TIMESTAMPS,
) -> OhlcvIntegrityReport:
    """Inspect raw or normalized bars for gaps and irregular open times."""

    if max_reported < 1:
        raise ValueError("max_reported must be >= 1")
    unordered = _input_was_unordered(bars)
    duration = timeframe_duration(timeframe)
    duration_seconds = timeframe_duration_seconds(timeframe)
    check_epoch = uses_epoch_alignment(timeframe)

    if not bars:
        return OhlcvIntegrityReport(
            timeframe=timeframe,
            bar_count=0,
            missing_open_times=(),
            unexpected_open_times=(),
            epoch_misaligned_open_times=(),
            missing_count=0,
            unexpected_count=0,
            truncated=False,
            input_was_unordered=unordered,
        )

    normalized = normalize_bars(bars)
    present = {bar.open_time for bar in normalized}
    first = normalized[0].open_time
    last = normalized[-1].open_time

    epoch_misaligned: list[datetime] = []
    if check_epoch:
        epoch_misaligned = [
            bar.open_time
            for bar in normalized
            if not _is_epoch_aligned(bar.open_time, duration_seconds)
        ]

    missing, unexpected, missing_count, unexpected_count, truncated = _grid_issues(
        first=first,
        last=last,
        duration=duration,
        present=present,
        max_reported=max_reported,
    )

    return OhlcvIntegrityReport(
        timeframe=timeframe,
        bar_count=len(normalized),
        missing_open_times=tuple(missing),
        unexpected_open_times=tuple(unexpected),
        epoch_misaligned_open_times=tuple(epoch_misaligned[:max_reported]),
        missing_count=missing_count,
        unexpected_count=unexpected_count,
        truncated=truncated or len(epoch_misaligned) > max_reported,
        input_was_unordered=unordered,
    )


def inspect_series(
    series: OhlcvSeries,
    *,
    max_reported: int = DEFAULT_MAX_REPORTED_TIMESTAMPS,
) -> OhlcvIntegrityReport:
    """Inspect an already-normalized ``OhlcvSeries``.

    ``input_was_unordered`` is always false here because ``OhlcvSeries`` sorts.
    """

    return inspect_ohlcv(series.bars, series.timeframe, max_reported=max_reported)


def require_contiguous_ohlcv(series: OhlcvSeries) -> OhlcvSeries:
    """Return ``series`` or raise if it has gaps, off-grid bars, or misalignment.

    Empty series and single-bar series are contiguous. Callers that persist a
    research dataset (later Parquet) should use this fail-closed helper.
    """

    report = inspect_series(series)
    if report.has_issues:
        raise IncompleteOhlcvHistory(
            f"OHLCV series {series.symbol} {series.timeframe} is not contiguous: "
            f"missing={report.missing_count} unexpected={report.unexpected_count} "
            f"epoch_misaligned={len(report.epoch_misaligned_open_times)}",
            report=report,
        )
    return series


def log_integrity_issues(series: OhlcvSeries) -> OhlcvIntegrityReport:
    """Inspect a series and log a warning when the window is not a clean grid."""

    report = inspect_series(series)
    if report.has_issues:
        logger.warning(
            "ohlcv integrity issues provider=%s symbol=%s timeframe=%s "
            "missing=%s unexpected=%s epoch_misaligned=%s truncated=%s",
            series.provider,
            series.symbol,
            series.timeframe,
            report.missing_count,
            report.unexpected_count,
            len(report.epoch_misaligned_open_times),
            report.truncated,
        )
    return report


_MAX_GRID_STEPS = 500_000


def _grid_issues(
    *,
    first: datetime,
    last: datetime,
    duration: timedelta,
    present: set[datetime],
    max_reported: int,
) -> tuple[list[datetime], list[datetime], int, int, bool]:
    expected: set[datetime] = set()
    cursor = first
    truncated = False
    steps = 0
    while cursor <= last:
        expected.add(cursor)
        steps += 1
        if steps >= _MAX_GRID_STEPS:
            truncated = True
            break
        cursor = cursor + duration

    missing_all = sorted(time for time in expected if time not in present)
    unexpected_all = sorted(time for time in present if time not in expected)
    if truncated:
        scanned_last = max(expected)
        unexpected_all = [time for time in unexpected_all if time <= scanned_last]
    missing_count = len(missing_all)
    unexpected_count = len(unexpected_all)
    truncated = truncated or len(missing_all) > max_reported or len(unexpected_all) > max_reported
    return (
        missing_all[:max_reported],
        unexpected_all[:max_reported],
        missing_count,
        unexpected_count,
        truncated,
    )
