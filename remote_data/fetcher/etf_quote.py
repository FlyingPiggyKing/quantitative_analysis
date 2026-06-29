"""ETF quote fetcher.

Per `etf-fetcher` spec: returns one record per symbol containing `symbol`, `ts`,
`price`, `pre_market_price`, `post_market_price`, `volume`.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from remote_data.config import load_config
from remote_data.fetcher.base import (
    RetryPolicy,
    epoch_to_iso,
    per_symbol,
    with_retry,
)

logger = logging.getLogger(__name__)


def _fetch_one(symbol: str) -> Dict[str, Any] | None:
    cfg = load_config()
    # Local import so the rest of the package loads even if yahooquery is absent.
    from yahooquery import Ticker  # type: ignore

    t = Ticker(symbol)
    policy = RetryPolicy(
        max_retries=cfg.yahooquery_max_retries,
        backoff_seconds=cfg.yahooquery_backoff_seconds,
    )

    def _do():
        details = t.price or {}
        if isinstance(details, dict) and symbol in details:
            row = details[symbol]
        elif isinstance(details, dict):
            row = details
        else:
            row = {}
        if not row:
            # Treat "no data" as transient — sometimes yahooquery returns {} on
            # cold-cache; the next retry typically fills in.
            raise RuntimeError(f"empty price response for {symbol}")
        return row

    raw = with_retry(_do, policy=policy)

    ts_epoch = raw.get("regularMarketTime") or raw.get("preMarketTime") or raw.get("postMarketTime")
    ts_iso = epoch_to_iso(ts_epoch) if ts_epoch is not None else None

    return {
        "symbol": symbol,
        "ts": ts_iso,
        "price": raw.get("regularMarketPrice"),
        "pre_market_price": raw.get("preMarketPrice"),
        "post_market_price": raw.get("postMarketPrice"),
        "volume": raw.get("regularMarketVolume"),
    }


def fetch_quotes(symbols: List[str]) -> List[Dict[str, Any]]:
    return per_symbol(symbols, _fetch_one)