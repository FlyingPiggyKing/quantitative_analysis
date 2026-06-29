"""ETF multi-period performance fetcher."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from remote_data.config import load_config
from remote_data.fetcher.base import RetryPolicy, per_symbol, with_retry

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
        info = t.fund_performance or {}
        if isinstance(info, dict):
            row = info.get(symbol, info)
        else:
            row = {}
        if not row:
            raise RuntimeError(f"empty performance for {symbol}")
        return row

    raw = with_retry(_do, policy=policy)

    # yahooquery returns nested structure with `performanceOverview` and
    # `trailingReturns` blocks. We map the multi-period returns to a flat shape.
    overview = (
        raw.get("performanceOverview")
        or raw.get("trailingReturns")
        or raw
    )

    def _f(keys: list[str]) -> float | None:
        for k in keys:
            v = overview.get(k)
            if v is None:
                continue
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
        return None

    return {
        "symbol": symbol,
        "as_of_date": raw.get("asOfDate") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "ytd_return": _f(["ytdReturn", "ytd"]),
        "return_1y": _f(["oneYearReturn", "trailingOneYearReturn", "1y"]),
        "return_3y": _f(["threeYearReturn", "trailingThreeYearReturn", "3y"]),
        "return_5y": _f(["fiveYearReturn", "trailingFiveYearReturn", "5y"]),
        "return_10y": _f(["tenYearReturn", "trailingTenYearReturn", "10y"]),
    }


def fetch_performance(symbols: List[str]) -> List[Dict[str, Any]]:
    return per_symbol(symbols, _fetch_one)