"""Base utilities for fetchers.

Per `etf-fetcher` spec §3:
- Ticker factory
- Retry/backoff helper for transient errors (HTTP 429, 5xx, connection)
- Per-symbol exception isolation (one symbol fails, others continue)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable, List, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class RetryPolicy:
    max_retries: int = 3
    backoff_seconds: float = 2.0

    def delays(self) -> Iterable[float]:
        """Backoff schedule: initial, x4, x16, ... capped by max_retries."""
        delay = self.backoff_seconds
        for _ in range(self.max_retries):
            yield delay
            delay *= 4


# Transient error categories we treat as retryable. We deliberately do NOT
# import yahooquery at module level so this file stays dependency-light and
# easy to test.
TRANSIENT_ERROR_NAMES = frozenset({
    "HTTPError", "RequestsError", "YQLQueryError",
    "TooManyRequests", "RateLimitError",
})


def _is_transient(exc: Exception) -> bool:
    name = type(exc).__name__
    if name in TRANSIENT_ERROR_NAMES:
        return True
    # Connection-style errors from urllib3 / httpx / requests.
    msg = str(exc).lower()
    return any(
        needle in msg
        for needle in ("timeout", "connection", "rate limit", "too many requests", "503", "502", "500")
    )


def with_retry(fn: Callable[[], T], *, policy: RetryPolicy) -> T:
    """Run `fn` with exponential backoff on transient errors."""
    last_exc: Exception | None = None
    for attempt, delay in enumerate([0.0, *policy.delays()]):
        if delay:
            logger.debug("retry attempt %d after %.1fs", attempt + 1, delay)
            time.sleep(delay)
        try:
            return fn()
        except Exception as exc:
            if not _is_transient(exc):
                raise
            last_exc = exc
            logger.warning(
                "transient error on attempt %d (%s): %s",
                attempt + 1, type(exc).__name__, exc,
            )
    assert last_exc is not None
    raise last_exc


# ---------------------------------------------------------------------------
# Normalization helpers
# ---------------------------------------------------------------------------


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def epoch_to_iso(ts: float | int | None) -> str | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (OverflowError, OSError, ValueError, TypeError):
        return None


def _coerce_float(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        # yahooquery sometimes returns "--" / "N/A" through pandas-aware casts.
        if f != f:  # NaN check
            return None
        return f
    except (TypeError, ValueError):
        return None


def _coerce_int(v) -> int | None:
    f = _coerce_float(v)
    return int(f) if f is not None else None


def per_symbol(symbols: List[str], fn: Callable[[str], T | None]) -> List[T]:
    """Apply `fn` per symbol. Per-symbol exceptions are caught and logged;
    the resulting list contains only successful results.

    This is the core guarantee: ONE failing symbol MUST NOT raise.
    """
    results: List[T] = []
    for s in symbols:
        try:
            r = fn(s)
        except Exception as exc:
            logger.warning(
                "symbol %s failed in fetcher: %s: %s",
                s, type(exc).__name__, exc,
            )
            continue
        if r is not None:
            results.append(r)
    return results


__all__ = [
    "RetryPolicy",
    "with_retry",
    "now_utc_iso",
    "epoch_to_iso",
    "per_symbol",
    "_coerce_float",
    "_coerce_int",
]