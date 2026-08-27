from app.market_data.errors import MarketDataError
from app.market_data.reconnect import ReconnectPolicy, reconnect_backoff_seconds


def test_reconnect_backoff_is_deterministic_with_injected_rng() -> None:
    policy = ReconnectPolicy(
        initial_backoff_seconds=1.0,
        max_backoff_seconds=8.0,
        jitter_ratio=0.5,
    )
    first = reconnect_backoff_seconds(0, policy, rng=lambda: 0.0)
    second = reconnect_backoff_seconds(1, policy, rng=lambda: 1.0)
    assert first == 1.0
    assert second == 3.0


def test_reconnect_backoff_caps_at_max() -> None:
    policy = ReconnectPolicy(
        initial_backoff_seconds=1.0,
        max_backoff_seconds=4.0,
        jitter_ratio=0.0,
    )
    assert reconnect_backoff_seconds(10, policy, rng=lambda: 0.0) == 4.0


def test_reconnect_policy_rejects_invalid_attempts() -> None:
    try:
        ReconnectPolicy(max_attempts=0)
    except MarketDataError as exc:
        assert "max_attempts" in str(exc)
    else:
        raise AssertionError("expected MarketDataError")
