import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.errors import DomainError, InvalidFinancialValue, InvalidTimestamp
from app.domain.market import MarketSnapshot, OhlcvBar
from app.domain.money import decimal_from_text, decimal_to_text, parse_decimal
from app.domain.order import Fill, OrderIntent, PositionSide
from app.domain.portfolio import PortfolioState
from app.domain.position import Position, PositionStatus
from app.domain.risk import RiskDecision, RiskVerdict
from app.domain.signal import Signal, SignalSide


def _utc(hour: int = 12) -> datetime:
    return datetime(2026, 8, 27, hour, 0, tzinfo=UTC)


def _bar() -> OhlcvBar:
    return OhlcvBar(
        open_time=_utc(8),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
        volume=Decimal("12.5"),
    )


def test_parse_decimal_rejects_float() -> None:
    with pytest.raises(InvalidFinancialValue, match="binary float"):
        parse_decimal(0.1, field="price")


def test_parse_decimal_rejects_bool() -> None:
    with pytest.raises(InvalidFinancialValue):
        parse_decimal(True, field="qty")


def test_parse_decimal_rejects_nan() -> None:
    with pytest.raises(InvalidFinancialValue, match="finite"):
        parse_decimal(Decimal("NaN"), field="price")


def test_decimal_text_round_trip_preserves_value() -> None:
    original = parse_decimal("0.00000001", field="price")
    text = decimal_to_text(original)
    assert "." in text
    assert "E" not in text and "e" not in text
    restored = decimal_from_text(text, field="price")
    assert restored == original


def test_decimal_addition_is_exact() -> None:
    total = parse_decimal("0.1", field="a") + parse_decimal("0.2", field="b")
    assert total == parse_decimal("0.3", field="sum")
    assert decimal_to_text(total) == "0.3"


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(InvalidTimestamp, match="naive"):
        OhlcvBar(
            open_time=datetime(2026, 8, 27, 8, 0),
            open=Decimal("1"),
            high=Decimal("1"),
            low=Decimal("1"),
            close=Decimal("1"),
            volume=Decimal("0"),
        )


def test_non_utc_offset_is_rejected() -> None:
    from datetime import timezone

    tehran = timezone(timedelta(hours=3, minutes=30))
    with pytest.raises(InvalidTimestamp, match="UTC"):
        OhlcvBar(
            open_time=datetime(2026, 8, 27, 8, 0, tzinfo=tehran),
            open=Decimal("1"),
            high=Decimal("1"),
            low=Decimal("1"),
            close=Decimal("1"),
            volume=Decimal("0"),
        )


def test_market_snapshot_rejects_look_ahead_bar() -> None:
    bar = _bar()
    with pytest.raises(ValueError, match="look-ahead"):
        MarketSnapshot(
            symbol="BTC/USDT",
            timeframe="4h",
            timestamp=_utc(7),
            bar=bar,
            provider="bybit",
        )


def test_ohlcv_rejects_high_below_low() -> None:
    with pytest.raises(ValueError, match="below low"):
        OhlcvBar(
            open_time=_utc(),
            open=Decimal("100"),
            high=Decimal("90"),
            low=Decimal("95"),
            close=Decimal("100"),
            volume=Decimal("1"),
        )


def test_signal_has_no_position_size_field() -> None:
    signal = Signal(
        signal_id=uuid4(),
        strategy_name="trend_v1",
        strategy_version="1.0.0",
        symbol="BTC/USDT",
        timeframe="4h",
        side=SignalSide.LONG,
        trigger_price=Decimal("105.5"),
        stop_model="atr_multiple",
        exit_model="trailing_atr",
        created_at=_utc(),
        dataset_hash="abc123",
    )
    assert not hasattr(signal, "position_size")
    wire = signal.to_wire()
    assert "position_size" not in wire
    assert wire["trigger_price"] == "105.5"
    assert isinstance(wire["trigger_price"], str)


def test_rejected_risk_decision_requires_zero_size_and_reason() -> None:
    with pytest.raises(ValueError, match="reason_code"):
        RiskDecision(
            decision_id=uuid4(),
            signal_id=uuid4(),
            verdict=RiskVerdict.REJECTED,
            reason_codes=(),
            calculated_size=Decimal("0"),
            estimated_risk_usd=Decimal("0"),
            estimated_risk_pct=Decimal("0"),
            portfolio_open_risk_pct=Decimal("0"),
            created_at=_utc(),
        )
    with pytest.raises(ValueError, match="calculated_size must be 0"):
        RiskDecision(
            decision_id=uuid4(),
            signal_id=uuid4(),
            verdict=RiskVerdict.REJECTED,
            reason_codes=("STALE_SIGNAL",),
            calculated_size=Decimal("1"),
            estimated_risk_usd=Decimal("0"),
            estimated_risk_pct=Decimal("0"),
            portfolio_open_risk_pct=Decimal("0"),
            created_at=_utc(),
        )


def test_approved_risk_decision_requires_positive_size() -> None:
    with pytest.raises(ValueError, match="calculated_size must be > 0"):
        RiskDecision(
            decision_id=uuid4(),
            signal_id=uuid4(),
            verdict=RiskVerdict.APPROVED,
            reason_codes=(),
            calculated_size=Decimal("0"),
            estimated_risk_usd=Decimal("10"),
            estimated_risk_pct=Decimal("0.005"),
            portfolio_open_risk_pct=Decimal("0.01"),
            created_at=_utc(),
        )


def test_order_intent_requires_client_order_id() -> None:
    with pytest.raises(DomainError, match="client_order_id"):
        OrderIntent(
            intent_id=uuid4(),
            signal_id=uuid4(),
            risk_decision_id=uuid4(),
            client_order_id="  ",
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            quantity=Decimal("0.01"),
            created_at=_utc(),
        )


def test_fill_and_order_wire_format_uses_decimal_strings() -> None:
    order_id = uuid4()
    fill = Fill(
        fill_id=uuid4(),
        order_id=order_id,
        client_order_id="nt-client-1",
        quantity=Decimal("0.010"),
        price=Decimal("65000.50"),
        fee=Decimal("0.00000001"),
        filled_at=_utc(),
    )
    payload = fill.to_wire()
    assert payload["price"] == "65000.50"
    assert payload["fee"] == "0.00000001"
    assert payload["quantity"] == "0.010"
    restored = decimal_from_text(payload["price"], field="price")
    assert restored == Decimal("65000.50")
    dumped = json.loads(json.dumps(payload))
    assert dumped["price"] == "65000.50"
    assert dumped["fee"] == "0.00000001"


def test_portfolio_state_wire_round_trip() -> None:
    state = PortfolioState(
        as_of=_utc(),
        equity=Decimal("10000.00"),
        cash_balance=Decimal("10000.00"),
        open_position_count=0,
        open_risk_pct=Decimal("0"),
        daily_realized_pnl=Decimal("-12.5"),
        daily_unrealized_pnl=Decimal("0"),
    )
    wire = state.to_wire()
    assert wire["equity"] == "10000.00"
    assert wire["daily_realized_pnl"] == "-12.5"
    assert decimal_from_text(str(wire["equity"]), field="equity") == Decimal("10000.00")


def test_closed_position_must_have_zero_quantity() -> None:
    with pytest.raises(ValueError, match="quantity 0"):
        Position(
            position_id=uuid4(),
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            status=PositionStatus.CLOSED,
            quantity=Decimal("1"),
            avg_entry_price=Decimal("100"),
            realized_pnl=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            opened_at=_utc(),
        )
