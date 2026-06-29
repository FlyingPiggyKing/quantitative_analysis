"""ETF fundamentals fetcher (current PE / PB / dividend yield)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from remote_data.config import load_config
from remote_data.fetcher.base import (
    RetryPolicy,
    now_utc_iso,
    per_symbol,
    with_retry,
)

logger = logging.getLogger(__name__)


def _fetch_one(symbol: str) -> Dict[str, Any] | None:
    cfg = load_config()
    from yahooquery import Ticker  # type: ignore

    t = Ticker(symbol)
    policy = RetryPolicy(
        max_retries=cfg.yahooquery_max_retries,
        backoff_seconds=cfg.yahooquery_backoff_seconds,
    )

    def _do():
        sd = t.summary_detail or {}
        ks = t.key_stats or {}
        row = {}
        if isinstance(sd, dict):
            row.update(sd.get(symbol, {}) if symbol in sd else sd)
        if isinstance(ks, dict):
            ks_row = ks.get(symbol, {}) if symbol in ks else ks
            # key_stats fields like `trailingPE`, `priceToBook` overlap with
            # summary_detail; merge with summary_detail winning for clarity.
            for k, v in ks_row.items():
                row.setdefault(k, v)
        if not row:
            raise RuntimeError(f"empty fundamentals for {symbol}")
        return row

    raw = with_retry(_do, policy=policy)

    def _f(keys: list[str]) -> float | None:
        for k in keys:
            v = raw.get(k)
            if v is not None:
                try:
                    return float(v)
                except (TypeError, ValueError):
                    continue
        return None

    return {
        "symbol": symbol,
        "as_of": now_utc_iso(),
        "pe": _f(["trailingPE", "forwardPE"]),
        "pb": _f(["priceToBook"]),
        "dividend_yield": _f(["dividendYield", "trailingAnnualDividendYield"]),
        "dividend_rate": _f(["dividendRate", "trailingAnnualDividendRate"]),
    }


def fetch_fundamentals(symbols: List[str]) -> List[Dict[str, Any]]:
    return per_symbol(symbols, _fetch_one)