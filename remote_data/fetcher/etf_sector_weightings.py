"""ETF sector-weight fetcher."""

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
        info = t.fund_sector_weightings or {}
        if isinstance(info, dict):
            row = info.get(symbol, info)
        else:
            row = {}
        if not row:
            raise RuntimeError(f"empty sector weightings for {symbol}")
        return row

    raw = with_retry(_do, policy=policy)

    sectors_raw = raw.get("sectors") or raw.get("sectorWeightings") or raw
    out = []
    if isinstance(sectors_raw, dict):
        for sector, weight in sectors_raw.items():
            out.append({"sector": sector, "weight_pct": weight})
    elif isinstance(sectors_raw, list):
        for entry in sectors_raw:
            if isinstance(entry, dict):
                out.append({
                    "sector": entry.get("sector") or entry.get("name"),
                    "weight_pct": entry.get("weight") or entry.get("weight_pct"),
                })

    return {
        "symbol": symbol,
        "as_of_date": raw.get("asOfDate") or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "sectors": out,
    }


def fetch_sector_weightings(symbols: List[str]) -> List[Dict[str, Any]]:
    return per_symbol(symbols, _fetch_one)