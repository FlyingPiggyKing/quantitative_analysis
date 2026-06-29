"""ETF top-holdings fetcher.

Returns `holdings`: [{symbol, name, weight_pct}, ...] per ETF.
"""

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
        # yahooquery exposes `fund_holding_info` for ETF holdings.
        info = t.fund_holding_info or {}
        if isinstance(info, dict):
            row = info.get(symbol, info)
        else:
            row = {}
        if not row:
            raise RuntimeError(f"empty holdings for {symbol}")
        return row

    raw = with_retry(_do, policy=policy)

    holdings_raw = raw.get("holdings") or raw.get("topHoldings") or {}
    out = []
    # `holdings` can be a dict {symbol: {name, weight}} or a list.
    if isinstance(holdings_raw, dict):
        for sym, h in list(holdings_raw.items())[:10]:
            if isinstance(h, dict):
                out.append({
                    "symbol": sym,
                    "name": h.get("name") or h.get("holdingName"),
                    "weight_pct": h.get("weight") or h.get("holdingPercent"),
                })
            else:
                out.append({"symbol": sym, "name": None, "weight_pct": h})
    elif isinstance(holdings_raw, list):
        for h in holdings_raw[:10]:
            if not isinstance(h, dict):
                continue
            out.append({
                "symbol": h.get("symbol") or h.get("holdingSymbol"),
                "name": h.get("name") or h.get("holdingName"),
                "weight_pct": h.get("weight") or h.get("holdingPercent"),
            })

    as_of_date = (
        raw.get("asOfDate")
        or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    )

    return {
        "symbol": symbol,
        "as_of_date": as_of_date,
        "holdings": out,
    }


def fetch_holdings(symbols: List[str]) -> List[Dict[str, Any]]:
    return per_symbol(symbols, _fetch_one)