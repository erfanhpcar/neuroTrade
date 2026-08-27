"""Generic explicit state-machine helper."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from typing import TypeVar

from app.domain.errors import InvalidStateTransition

S = TypeVar("S", bound=Enum)


def assert_allowed_transition(
    entity: str,
    current: S,
    target: S,
    allowed: Mapping[S, frozenset[S]],
) -> None:
    if target not in allowed[current]:
        raise InvalidStateTransition(entity, str(current.value), str(target.value))
