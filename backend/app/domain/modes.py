"""Operational trading modes.

These are locked semantics defined in `docs/01_ARCH_OVERVIEW.md`. `PAPER` is the
safe default everywhere; live execution (`FULL`) must never be reached implicitly.
"""

from __future__ import annotations

from enum import StrEnum


class TradingMode(StrEnum):
    """Operational mode of the trading system.

    - ``PAPER``: no real orders are ever sent (safe default).
    - ``SEMI``: signal + risk decision require explicit operator approval before execution.
    - ``FULL``: signal + risk decision execute directly; only after formal promotion.
    - ``HALTED``: new exposure is blocked; existing positions managed per policy.
    """

    PAPER = "PAPER"
    SEMI = "SEMI"
    FULL = "FULL"
    HALTED = "HALTED"
