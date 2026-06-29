"""One-shot backfill on startup: populate `etf_fundamentals` if the table is empty.

Per `etf-scheduler` spec §"Backfill task":
- Run only when `etf_fundamentals` is empty
- Fetch current snapshot for all symbols
- Best-effort fetch of up to 2 years of `valuation_measures` history (acknowledged
  in the design that this returns ~2 years of quarterly data for stocks, no data
  for ETFs — the row is written regardless)
- Write a `backfill_complete` row to `fetch_log` on success
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from remote_data.config import Config, load_config
from remote_data.fetcher.etf_fundamentals import fetch_fundamentals
from remote_data.store import local_db

logger = logging.getLogger(__name__)


def _table_empty(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.execute(f"SELECT 1 FROM {table} LIMIT 1")
    return cur.fetchone() is None


def run_once(conn: sqlite3.Connection, cfg: Optional[Config] = None) -> int:
    """Run the backfill if `etf_fundamentals` is empty. Returns rows inserted."""
    cfg = cfg or load_config()

    if not _table_empty(conn, "etf_fundamentals"):
        logger.info("backfill skipped: etf_fundamentals already populated")
        return 0

    logger.info("backfill start symbols=%d", len(cfg.symbols))
    try:
        records = fetch_fundamentals(cfg.symbols)
    except Exception as exc:
        logger.error("backfill fetch failed: %s", exc)
        local_db.record_fetch(
            conn, data_type="etf_fundamentals", symbol=None, status="error",
            error=str(exc), row_count=None,
        )
        return 0

    n = local_db.insert_etf_fundamentals(conn, records)
    local_db.record_fetch(
        conn, data_type="etf_fundamentals", symbol=None,
        status="ok", error=None, row_count=n,
    )
    logger.info("backfill complete: inserted %d etf_fundamentals rows", n)
    return n


def maybe_backfill(conn: sqlite3.Connection, cfg: Optional[Config] = None) -> int:
    """Alias kept for symmetry with scheduler.wiring."""
    return run_once(conn, cfg)