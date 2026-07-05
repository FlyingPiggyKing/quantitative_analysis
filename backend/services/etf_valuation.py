"""ETF-aware wrapper for US stock valuation responses.

Routes US-stock valuation through `FutuQuoteService.get_daily_basic` and, when
the requested symbol is recognised as an ETF, merges the latest yahooquery
fundamentals row from `etf_remote.db.etf_fundamentals` into the response.

The "is this symbol an ETF?" decision is dynamic: the symbol set is loaded
once from `SELECT DISTINCT symbol FROM etf_fundamentals` and cached in memory
for O(1) membership tests. `refresh_etf_symbols()` invalidates the cache so
the next `is_etf()` call repopulates from the database.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Set

from backend.services import etf_service
from backend.services.futu_quote_service import FutuQuoteService

logger = logging.getLogger(__name__)

# Module-level cache. `None` means "not yet loaded"; an empty set after a load
# means "we queried the DB and found zero ETF symbols" (still a valid cache hit).
_ETF_SYMBOLS: Optional[Set[str]] = None


def _load_etf_symbols() -> Set[str]:
    """Read distinct ETF symbols from `etf_fundamentals` into the cache.

    Stored uppercased so `is_etf()` can do a case-insensitive membership check.
    Returns the loaded set so callers (incl. `refresh_etf_symbols`) can reuse it.
    """
    global _ETF_SYMBOLS
    conn = etf_service.get_conn()
    try:
        rows = conn.execute(
            "SELECT DISTINCT symbol FROM etf_fundamentals"
        ).fetchall()
        symbols = {str(r["symbol"]).upper() for r in rows if r["symbol"]}
    finally:
        conn.close()
    _ETF_SYMBOLS = symbols
    logger.info(f"[ETF-VAL] Loaded {len(symbols)} ETF symbols into cache")
    return symbols


def is_etf(symbol: str) -> bool:
    """True if `symbol` appears in the cached ETF symbol set.

    Triggers a lazy DB load on first call. Subsequent calls are O(1).
    Symbols are matched case-insensitively (cache stores uppercase).
    """
    if _ETF_SYMBOLS is None:
        _load_etf_symbols()
    assert _ETF_SYMBOLS is not None
    return symbol.upper() in _ETF_SYMBOLS


def refresh_etf_symbols() -> Set[str]:
    """Discard the cached set and force the next `is_etf()` to repopulate.

    Returns the freshly-loaded set. Intended to be called after each pusher
    ingest so a newly added ETF symbol takes effect without a restart.
    """
    global _ETF_SYMBOLS
    _ETF_SYMBOLS = None
    return _load_etf_symbols()


def get_etf_aware_daily_basic(symbol: str, days: int = 30) -> Dict[str, Any]:
    """Get daily basic valuation, enriched with ETF fundamentals for ETFs.

    Always delegates to `FutuQuoteService.get_daily_basic` for the historical
    series + market-cap snapshot. When the symbol is an ETF, merges the most
    recent `etf_fundamentals` row (pe / pb / dividend_yield / dividend_rate /
    as_of) into the `latest` record and adds top-level `is_etf: true`.

    Non-ETF symbols get `is_etf: false` and null dividend fields added but
    every existing key is preserved.
    """
    base = FutuQuoteService.get_daily_basic(symbol, days)
    # Futu error path: pass through with `is_etf: false`, no exception.
    if "error" in base:
        base["is_etf"] = False
        return base

    if not is_etf(symbol):
        base["is_etf"] = False
        latest = base.get("latest")
        if isinstance(latest, dict):
            latest["dividend_yield"] = None
            latest["dividend_rate"] = None
            latest["as_of"] = None
        return base

    # ETF branch: merge yahooquery fundamentals.
    base["is_etf"] = True
    latest = base.get("latest")
    if not isinstance(latest, dict):
        # Defensive: ensure the ETF shape is uniform even if Futu gave no latest.
        latest = {}
        base["latest"] = latest

    row = etf_service.get_fundamentals(symbol)
    if row is not None:
        # Always take the yahooquery value, even when null — yahooquery is the
        # authoritative source for ETF fundamentals.
        latest["pe_ttm"] = row.get("pe")
        latest["pb"] = row.get("pb")
        latest["dividend_yield"] = row.get("dividend_yield")
        latest["dividend_rate"] = row.get("dividend_rate")
        latest["as_of"] = row.get("as_of")
    else:
        # ETF symbol known, but no current row — keep Futu values, null dividend fields.
        latest["dividend_yield"] = None
        latest["dividend_rate"] = None
        latest["as_of"] = None

    return base