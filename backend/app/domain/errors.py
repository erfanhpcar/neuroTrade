"""Domain-layer errors. These must not depend on HTTP or persistence frameworks."""


class DomainError(ValueError):
    """Base error for invalid domain values or transitions."""


class InvalidFinancialValue(DomainError):
    """A price, quantity, fee, or other money field is not a finite Decimal."""


class InvalidTimestamp(DomainError):
    """A timestamp is naive or not UTC."""


class InvalidStateTransition(DomainError):
    """An entity was asked to move to a status that the state machine forbids."""

    def __init__(self, entity: str, current: str, target: str) -> None:
        self.entity = entity
        self.current = current
        self.target = target
        super().__init__(f"invalid {entity} transition: {current} -> {target}")
