from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def bounded_read(call: Callable[[], T], *, attempts: int = 3,
                 retryable: tuple[type[Exception], ...] = (TimeoutError,)) -> T:
    """Retry only read operations and only for explicitly transient failures."""
    if attempts < 1:
        raise ValueError("attempts must be positive")
    for attempt in range(1, attempts + 1):
        try:
            return call()
        except retryable:
            if attempt == attempts:
                raise
    raise AssertionError("unreachable")
