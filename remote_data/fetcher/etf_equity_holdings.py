"""ETF equity holdings fetcher — per-holding PE / PB / PS."""

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
        # yahooquery's `fund_holding_info` exposes holdings; equity-specific
        # PE/PB/PS is not always present. We record whatever is available.
        info = t.fund_holding_info or {}
        if isinstance(info, dict):
            row = info.get(symbol, info)
        else:
            row = {}
        if not row:
            raise RuntimeError(f"empty equity holdings for {symbol}")
        return row

    raw = with_retry(_do, policy=policy)

    holdings_raw = raw.get("holdings") or {}
    out = []
    if isinstance(holdings_raw, dict):
        for sym, h in list(holdings_raw.items())[:50]:
            if not isinstance(h, dict):
                continue
            out.append({
                "symbol": sym,
                "name": h.get("name") or h.get("holdingName"),
                "weight_pct": h.get("weight") or h.get("holdingPercent"),
                "pe": h.get("pe") or h.get("trailingPE"),
                "pb": h.get("pb") or h.get("priceToBook"),
                "ps": h.get("ps") or h.get("priceToSalesTrailing12Months"),
            })

    return {
        "symbol": symbol,
        "as_of_date": raw.get("asOfDate") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "holdings": out,
    }


def fetch_equity_holdings(symbols: List[str]) -> List[Dict[str, Any]]:
    return per_symbol(symbols, _fetch_one)