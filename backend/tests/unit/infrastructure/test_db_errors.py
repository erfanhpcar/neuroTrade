from sqlalchemy.exc import IntegrityError

from app.infrastructure.db.errors import (
    DuplicateClientOrderId,
    DuplicateExchangeOrderId,
    PersistenceError,
    map_integrity_error,
)


def test_map_integrity_error_duplicate_client_order_id() -> None:
    orig = Exception(
        'duplicate key value violates unique constraint "uq_orders_client_order_id"\n'
        "DETAIL:  Key (client_order_id)=(nt-dup-1) already exists."
    )
    mapped = map_integrity_error(IntegrityError("INSERT", {}, orig))
    assert isinstance(mapped, DuplicateClientOrderId)
    assert mapped.client_order_id == "nt-dup-1"
    assert "nt-dup-1" in str(mapped)


def test_map_integrity_error_duplicate_exchange_order_id() -> None:
    orig = Exception(
        'duplicate key value violates unique constraint "uq_orders_exchange_order_id"\n'
        "DETAIL:  Key (exchange_order_id)=(ex-1) already exists."
    )
    mapped = map_integrity_error(IntegrityError("INSERT", {}, orig))
    assert isinstance(mapped, DuplicateExchangeOrderId)
    assert mapped.exchange_order_id == "ex-1"


def test_map_integrity_error_generic_has_no_dsn_or_password() -> None:
    orig = Exception("foreign key constraint failed")
    mapped = map_integrity_error(IntegrityError("INSERT", {}, orig))
    assert isinstance(mapped, PersistenceError)
    assert not isinstance(mapped, DuplicateClientOrderId)
    assert "neurotrade_dev_password" not in str(mapped)
    assert "postgresql+asyncpg://" not in str(mapped)
    assert str(mapped) == "integrity error"
