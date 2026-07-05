"""Read-only monitoring of the overseas → domestic ETF push pipeline.

Surfaces, for each business table in `etf_remote.db`:
- when the pusher last sent us a batch (from `etf_ingest_log.received_at`)
- the latest business date stored in the table itself
- a freshness status derived from configurable thresholds

The connection is opened with SQLite `mode=ro` so this module can never
interfere with the live ingest writer.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# (data_type, table, date_column, label_zh)
# One row per business table defined in migrations/etf_schema.sql.
TABLE_SPECS: list[tuple[str, str, str, str]] = [
    ("etf_quote", "etf_quote", "ts", "实时报价"),
    ("etf_fundamentals", "etf_fundamentals", "as_of", "基本面"),
    ("etf_holdings", "etf_holdings", "as_of_date", "持仓"),
    ("etf_sector_weights", "etf_sector_weights", "as_of_date", "行业权重"),
    ("etf_performance", "etf_performance", "as_of_date", "业绩"),
    ("etf_equity_holdings", "etf_equity_holdings", "as_of_date", "成分股权重"),
    ("etf_esg", "etf_esg", "as_of_date", "ESG"),
    ("etf_news", "etf_news", "published_at", "新闻"),
]


def _resolve_warn_hours() -> float:
    """Hours below which a push counts as fresh."""
    return float(os.getenv("ETF_PUSH_WARN_HOURS", "6"))


def _resolve_stale_hours() -> float:
    """Hours above which a push counts as stale."""
    return float(os.getenv("ETF_PUSH_STALE_HOURS", "24"))


def _parse_iso(value: str | None) -> datetime | None:
    """Parse an ISO8601 timestamp; tolerate missing `Z` suffix and `+00:00`."""
    if not value:
        return None
    try:
        # `fromisoformat` rejects trailing `Z` on Python <3.11; normalize.
        cleaned = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def _classify(lag_hours: float | None, warn: float, stale: float) -> str:
    if lag_hours is None:
        return "unknown"
    if lag_hours <= warn:
        return "ok"
    if lag_hours <= stale:
        return "warn"
    return "stale"


def _summarize_table(
    conn: sqlite3.Connection,
    data_type: str,
    table: str,
    date_column: str,
    label_zh: str,
    now_utc: datetime,
    warn_hours: float,
    stale_hours: float,
) -> dict[str, Any]:
    last_received_at: str | None = conn.execute(
        "SELECT MAX(received_at) AS v FROM etf_ingest_log WHERE data_type = ?",
        (data_type,),
    ).fetchone()["v"]

    last_record_row = conn.execute(
        f'SELECT MAX("{date_column}") AS v FROM "{table}"'
    ).fetchone()
    last_record_date = last_record_row["v"] if last_record_row else None

    row_count = conn.execute(f'SELECT COUNT(*) AS n FROM "{table}"').fetchone()["n"]

    received_dt = _parse_iso(last_received_at)
    if received_dt is None:
        lag_hours: float | None = None
    else:
        lag_hours = round((now_utc - received_dt).total_seconds() / 3600, 2)

    return {
        "data_type": data_type,
        "label_zh": label_zh,
        "last_received_at": last_received_at,
        "last_record_date": last_record_date,
        "row_count": row_count,
        "lag_hours": lag_hours,
        "status": _classify(lag_hours, warn_hours, stale_hours),
    }


def compute_push_status(db_path: Path) -> dict[str, Any]:
    """Build the full per-table push health snapshot for `db_path`.

    Returns the dict shape consumed by the admin endpoint. On missing DB,
    returns the same shape with `tables: []` and an `error` field — the
    endpoint stays at HTTP 200 so the frontend can show a friendly message
    instead of an error overlay.
    """
    warn_hours = _resolve_warn_hours()
    stale_hours = _resolve_stale_hours()
    now_utc = datetime.now(timezone.utc).replace(microsecond=0)

    base = {
        "tables": [],
        "server_time": now_utc.isoformat().replace("+00:00", "Z"),
        "db_path": str(db_path),
        "thresholds": {"warn_hours": warn_hours, "stale_hours": stale_hours},
    }

    if not db_path.exists():
        return {**base, "error": "etf_remote.db not found"}

    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        tables = [
            _summarize_table(conn, dt, t, dc, lbl, now_utc, warn_hours, stale_hours)
            for dt, t, dc, lbl in TABLE_SPECS
        ]
    finally:
        conn.close()

    return {**base, "tables": tables}