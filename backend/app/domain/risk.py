"""Risk decision contract. Execution is unreachable without APPROVED."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from app.domain.fields import require_text, require_uuid
from app.domain.money import decimal_to_text, parse_decimal, require_non_negative_decimal
from app.domain.timestamps import require_utc


class RiskVerdict(StrEnum):
    """Documented RiskDecision outcomes from docs/03_RISK_FIREWALL.md."""

    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class RiskDecision:
    """Deterministic, auditable risk result for one Signal."""

    decision_id: UUID
    signal_id: UUID
    verdict: RiskVerdict
    reason_codes: tuple[str, ...]
    calculated_size: Decimal
    estimated_risk_usd: Decimal
    estimated_risk_pct: Decimal
    portfolio_open_risk_pct: Decimal
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "decision_id", require_uuid(self.decision_id, field="decision_id"))
        object.__setattr__(self, "signal_id", require_uuid(self.signal_id, field="signal_id"))
        if not isinstance(self.verdict, RiskVerdict):
            raise TypeError("verdict must be RiskVerdict")
        object.__setattr__(self, "reason_codes", _require_reason_codes(self.reason_codes))
        object.__setattr__(
            self,
            "calculated_size",
            require_non_negative_decimal(self.calculated_size, field="calculated_size"),
        )
        object.__setattr__(
            self,
            "estimated_risk_usd",
            require_non_negative_decimal(self.estimated_risk_usd, field="estimated_risk_usd"),
        )
        object.__setattr__(
            self,
            "estimated_risk_pct",
            require_non_negative_decimal(self.estimated_risk_pct, field="estimated_risk_pct"),
        )
        object.__setattr__(
            self,
            "portfolio_open_risk_pct",
            require_non_negative_decimal(
                self.portfolio_open_risk_pct, field="portfolio_open_risk_pct"
            ),
        )
        object.__setattr__(self, "created_at", require_utc(self.created_at, field="created_at"))
        if self.verdict is RiskVerdict.REJECTED and self.calculated_size != parse_decimal(
            "0", field="calculated_size"
        ):
            raise ValueError("REJECTED RiskDecision calculated_size must be 0")
        if self.verdict is RiskVerdict.APPROVED and self.calculated_size <= 0:
            raise ValueError("APPROVED RiskDecision calculated_size must be > 0")
        if self.verdict is RiskVerdict.REJECTED and not self.reason_codes:
            raise ValueError("REJECTED RiskDecision requires at least one reason_code")

    def to_wire(self) -> dict[str, object]:
        return {
            "decision_id": str(self.decision_id),
            "signal_id": str(self.signal_id),
            "verdict": self.verdict.value,
            "reason_codes": list(self.reason_codes),
            "calculated_size": decimal_to_text(self.calculated_size),
            "estimated_risk_usd": decimal_to_text(self.estimated_risk_usd),
            "estimated_risk_pct": decimal_to_text(self.estimated_risk_pct),
            "portfolio_open_risk_pct": decimal_to_text(self.portfolio_open_risk_pct),
            "created_at": self.created_at.isoformat(),
        }


def _require_reason_codes(value: object) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise TypeError("reason_codes must be a tuple of strings")
    return tuple(require_text(code, field="reason_codes") for code in value)
