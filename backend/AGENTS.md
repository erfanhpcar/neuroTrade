# Backend Agent Instructions

These instructions extend the root `AGENTS.md` for `backend/**`.

## Python and domain design

- Python 3.11+ with complete type hints for public functions, methods, and domain boundaries.
- Keep `domain/`, `strategies/`, `risk/`, and `portfolio/` framework-independent.
- Prefer dataclasses/Enums/protocols for domain concepts; use Pydantic at configuration/API/external-data boundaries where validation is needed.
- Async is for external I/O (exchange, DB, Redis, HTTP). Do not make pure strategy/risk functions async.
- Dependency direction points inward: adapters may depend on domain contracts; domain must not import adapters.
- No direct CCXT/native-exchange calls outside market-data/execution adapters.
- `market_data/` implements `MarketDataProvider`. Unit tests must use `ReplayMarketDataProvider`, fixtures, or an injected HTTP fake; they must not hit the public internet. Do not add CCXT. The first public venue adapter is native Bybit REST in `market_data/bybit.py`. Detect missing candles with `inspect_ohlcv` before treating a window as complete.

## Financial values

- Use `Decimal` for executable/persisted price, quantity, fee, balance, PnL, risk budget, and notional.
- Never construct `Decimal` from a binary float without deliberate string/quantization handling.
- Apply exchange tick-size/step-size/min-notional rules at the execution boundary before submission and verify the resulting risk again when rounding materially changes exposure.
- Store timestamps as timezone-aware UTC.

## Strategy and backtest

- Strategy feature calculations should be pure functions whenever possible.
- `Strategy.generate_signal()` must have no network, DB, Redis, clock, random, or order side effects.
- Explicitly inject current timestamp/data; never call "now" inside historical strategy evaluation.
- Deterministic results for the same dataset + strategy config are mandatory.
- Backtest execution models must not leak future high/low/close information into the decision timestamp.
- If intrabar order is ambiguous with candle-only data, use the documented deterministic policy; do not choose the profitable path.

## Risk and execution

- Risk decisions are deterministic and persisted/auditable.
- Reserve risk atomically before concurrent approved signals can become orders.
- Persist order intent/idempotency identity before or atomically with submission flow as designed.
- After exchange timeout/connection loss, reconcile before resubmission.
- Model order/position transitions explicitly and reject invalid transitions.
- Paper execution must implement the same adapter contract as private exchange execution.

## Persistence

- Use migrations for schema changes; no runtime `CREATE TABLE` shortcuts in production code.
- Constraints belong in the DB where they protect invariants (unique client IDs, valid references, etc.).
- Keep transaction boundaries explicit; avoid long transactions around network calls.
- Write trading state through `UnitOfWork` and repositories. Do not scatter `session.commit()`. Do not hold a transaction open across exchange I/O.
- Redis may optimize delivery/coordination but may not be required to reconstruct account/trading state.

## Errors and logs

- Define meaningful domain/external-boundary errors.
- Never silently ignore exchange reconciliation discrepancies.
- Structured logs should carry relevant IDs (`strategy_version`, `signal_id`, `client_order_id`, `position_id`, `backtest_run_id`).
- Redact secrets and sensitive request headers.

## Tests

- Use pytest for backend tests once the toolchain is bootstrapped.
- Prefer fixtures/fakes to network calls in unit tests.
- Add regression tests for every bug involving money, state transitions, duplicate orders, look-ahead, or reconciliation.
- Property/boundary tests are encouraged for position sizing and risk limits.
