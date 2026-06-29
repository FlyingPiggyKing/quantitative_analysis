"""ETF ESG scores fetcher."""

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
        info = t.fund_esg_scores or t.esg_scores or {}
        if isinstance(info, dict):
            row = info.get(symbol, info)
        else:
            row = {}
        if not row:
            raise RuntimeError(f"empty ESG scores for {symbol}")
        return row

    raw = with_retry(_do, policy=policy)

    def _f(keys: list[str]) -> float | None:
        for k in keys:
            v = raw.get(k)
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
        "total_esg": _f(["totalEsg", "esgScore", "total"]),
        "environment": _f(["environmentScore", "environment"]),
        "social": _f(["socialScore", "social"]),
        "governance": _f(["governanceScore", "governance"]),
    }


def fetch_esg(symbols: List[str]) -> List[Dict[str, Any]]:
    return per_symbol(symbols, _fetch_one)