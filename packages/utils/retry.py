"""Small retry helper for filesystem and generation steps."""

from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable


def retryable(attempts: int = 3, delay_seconds: float = 0.25) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_error: Exception | None = None
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:  # pragma: no cover - defensive helper
                    last_error = exc
                    if attempt == attempts:
                        break
                    time.sleep(delay_seconds * attempt)
            if last_error is None:
                raise RuntimeError("retryable wrapper exited without a result or exception")
            raise last_error

        return wrapper

    return decorator

