"""Persistence layer for the ETF remote database.

Encapsulates every read and write against `etf_remote.db`. Two consumers:
- The ingest service (`etf_ingest_service`) uses the `upsert_*` / `insert_news`
  methods to land incoming records.
- The read API (`etf_read`) uses the `get_*` / `list_symbols` methods to
  serve the frontend.

All writes use `INSERT ... ON CONFLICT(...) DO UPDATE` (UPSERT) keyed on
each table's natural PK so re-pushes are idempotent. `etf_news` is the
exception: it uses `INSERT OR IGNORE` on its `url` PK so duplicate news
items are dropped silently (per the spec).

Array-shaped fields (`holdings`, `sectors`, `equity_holdings`, `esg`) are
stored as JSON-serialized TEXT in `payload_json` columns and rehydrated on
read.
"""
from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional

from backend.services.etf_db import get_conn


# ---------------------------------------------------------------------------
# Writes — used by the ingest service
# ---------------------------------------------------------------------------


def upsert_quote(conn: sqlite3.Connection, rec: Dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO etf_quote(symbol, ts, price, pre_market_price, post_market_price, volume) "
        "VALUES(?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(symbol, ts) DO UPDATE SET "
        "price = excluded.price, pre_market_price = excluded.pre_market_price, "
        "post_market_price = excluded.post_market_price, volume = excluded.volume",
        (
            rec["symbol"],
            rec["ts"],
            rec.get("price"),
            rec.get("pre_market_price"),
            rec.get("post_market_price"),
            rec.get("volume"),
        ),
    )


def upsert_fundamentals(conn: sqlite3.Connection, rec: Dict[str, Any]) -> None:
    conn.execute(
        "INSERT INTO etf_fundamentals(symbol, as_of, pe, pb, dividend_yield, dividend_rate) "
        "VALUES(?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(symbol, as_of) DO UPDATE SET "
        "pe = excluded.pe, pb = excluded.pb, "
        "dividend_yield = excluded.dividend_yield, dividend_rate = excluded.dividend_rate",
        (
            rec["symbol"],
            rec["as_of"],
            rec.get("pe"),
            rec.get("pb"),
            rec.get("dividend_yield"),
            rec.get("dividend_rate"),
        ),
    )


def upsert_holdings(conn: sqlite3.Connection, rec: Dict[str, Any]) -> None:
    _upsert_payload(
        conn,
        table="etf_holdings",
        pk_cols=("symbol", "as_of_date"),
        rec=rec,
        array_field="holdings",
    )


def upsert_sector_weights(conn: sqlite3.Connection, rec: Dict[str, Any]) -> None:
    _upsert_payload(
        conn,
        table="etf_sector_weights",
        pk_cols=("symbol", "as_of_date"),
        rec=rec,
        array_field="sectors",
    )


def upsert_equity_holdings(conn: sqlite3.Connection, rec: Dict[str, Any]) -> None:
    _upsert_payload(
        conn,
        table="etf_equity_holdings",
        pk_cols=("symbol", "as_of_date"),
        rec=rec,
        array_field="holdings",
    )


def upsert_esg(conn: sqlite3.Connection, rec: Dict[str, Any]) -> None:
    """ESG stores its flat fields alongside the JSON for indexed reads.

    The wire payload is a flat record with `total_esg`, `environment`, `social`,
    `governance`. We store the same flat columns (so the read API can index
    `total_esg` cheaply) AND the JSON in `payload_json` for round-trip fidelity.
    """
    payload_json = json.dumps(
        {
            "total_esg": rec.get("total_esg"),
            "environment": rec.get("environment"),
            "social": rec.get("social"),
            "governance": rec.get("governance"),
        },
        ensure_ascii=False,
    )
    conn.execute(
        f"INSERT INTO etf_esg(symbol, as_of_date, payload_json) VALUES(?, ?, ?) "
        f"ON CONFLICT(symbol, as_of_date) DO UPDATE SET payload_json = excluded.payload_json",
        (rec["symbol"], rec["as_of_date"], payload_json),
    )


def upsert_performance(conn: sqlite3.Connection, rec: Dict[str, Any]) -> None:
    """Performance uses wire-format field names (ytd_return, return_1y, ...).

    SQL columns are the short forms per the etf-persistence spec. The dispatcher
    hands us the wire dict, so we map the keys here.
    """
    conn.execute(
        'INSERT INTO etf_performance(symbol, as_of_date, ytd, "1y", "3y", "5y", "10y") '
        "VALUES(?, ?, ?, ?, ?, ?, ?) "
        'ON CONFLICT(symbol, as_of_date) DO UPDATE SET '
        'ytd = excluded.ytd, "1y" = excluded."1y", '
        '"3y" = excluded."3y", "5y" = excluded."5y", "10y" = excluded."10y"',
        (
            rec["symbol"],
            rec["as_of_date"],
            rec.get("ytd_return"),
            rec.get("return_1y"),
            rec.get("return_3y"),
            rec.get("return_5y"),
            rec.get("return_10y"),
        ),
    )


def insert_news(conn: sqlite3.Connection, rec: Dict[str, Any]) -> bool:
    """INSERT OR IGNORE on url PK. Returns True if a new row was inserted."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO etf_news(url, symbol, title, publisher, published_at, summary) "
        "VALUES(?, ?, ?, ?, ?, ?)",
        (
            rec["url"],
            rec.get("symbol"),
            rec.get("title"),
            rec.get("publisher"),
            rec.get("published_at"),
            rec.get("summary"),
        ),
    )
    return cur.rowcount > 0


def _upsert_payload(
    conn: sqlite3.Connection,
    *,
    table: str,
    pk_cols: tuple,
    rec: Dict[str, Any],
    array_field: str,
) -> None:
    """Generic UPSERT for tables with `payload_json TEXT NOT NULL`.

    `pk_cols` is a 2-tuple of (pk_col1, pk_col2); the table has a composite
    primary key on those two columns (verified by the schema in
    `migrations/etf_schema.sql`).
    """
    payload_json = json.dumps(rec.get(array_field, []), ensure_ascii=False)
    conn.execute(
        f"INSERT INTO {table}({pk_cols[0]}, {pk_cols[1]}, payload_json) VALUES(?, ?, ?) "
        f"ON CONFLICT({pk_cols[0]}, {pk_cols[1]}) DO UPDATE SET payload_json = excluded.payload_json",
        (rec[pk_cols[0]], rec[pk_cols[1]], payload_json),
    )


# ---------------------------------------------------------------------------
# Reads — used by the read API
# ---------------------------------------------------------------------------


def get_latest_quote(symbol: str, limit: int = 480) -> List[Dict[str, Any]]:
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT ts, price, pre_market_price, post_market_price, volume "
            "FROM etf_quote WHERE symbol = ? ORDER BY ts DESC LIMIT ?",
            (symbol, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_fundamentals(symbol: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT as_of, pe, pb, dividend_yield, dividend_rate FROM etf_fundamentals "
            "WHERE symbol = ? ORDER BY as_of DESC LIMIT 1",
            (symbol,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_holdings(symbol: str) -> Optional[Dict[str, Any]]:
    return _get_payload_row("etf_holdings", symbol, "holdings")


def get_sector_weights(symbol: str) -> Optional[Dict[str, Any]]:
    return _get_payload_row("etf_sector_weights", symbol, "sectors")


def get_equity_holdings(symbol: str) -> Optional[Dict[str, Any]]:
    return _get_payload_row("etf_equity_holdings", symbol, "holdings")


def get_performance(symbol: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute(
            'SELECT as_of_date, ytd, "1y", "3y", "5y", "10y" FROM etf_performance '
            "WHERE symbol = ? ORDER BY as_of_date DESC LIMIT 1",
            (symbol,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        # Map short SQL column names to the spec's response field names.
        return {
            "symbol": symbol,
            "as_of_date": d["as_of_date"],
            "ytd": d.get("ytd"),
            "1y": d.get("1y"),
            "3y": d.get("3y"),
            "5y": d.get("5y"),
            "10y": d.get("10y"),
        }
    finally:
        conn.close()


def get_esg(symbol: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT as_of_date, payload_json FROM etf_esg "
            "WHERE symbol = ? ORDER BY as_of_date DESC LIMIT 1",
            (symbol,),
        ).fetchone()
        if not row:
            return None
        payload = json.loads(row["payload_json"]) if row["payload_json"] else {}
        return {
            "symbol": symbol,
            "as_of_date": row["as_of_date"],
            "total_esg": payload.get("total_esg"),
            "environment": payload.get("environment"),
            "social": payload.get("social"),
            "governance": payload.get("governance"),
        }
    finally:
        conn.close()


def get_news(symbol: str, page: int, page_size: int) -> Dict[str, Any]:
    """Paginated news, newest first. Returns total + page slice."""
    conn = get_conn()
    try:
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM etf_news WHERE symbol = ?",
            (symbol,),
        ).fetchone()["n"]
        offset = max(0, (page - 1) * page_size)
        rows = conn.execute(
            "SELECT url, title, publisher, published_at, summary FROM etf_news "
            "WHERE symbol = ? ORDER BY published_at DESC LIMIT ? OFFSET ?",
            (symbol, page_size, offset),
        ).fetchall()
        return {
            "total": total,
            "items": [dict(r) for r in rows],
        }
    finally:
        conn.close()


def list_symbols() -> List[str]:
    """Distinct symbols across all data tables, sorted alphabetically."""
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT symbol FROM etf_quote
            UNION SELECT symbol FROM etf_fundamentals
            UNION SELECT symbol FROM etf_holdings
            UNION SELECT symbol FROM etf_sector_weights
            UNION SELECT symbol FROM etf_performance
            UNION SELECT symbol FROM etf_equity_holdings
            UNION SELECT symbol FROM etf_esg
            UNION SELECT symbol FROM etf_news
            ORDER BY symbol
            """
        ).fetchall()
        return [r["symbol"] for r in rows]
    finally:
        conn.close()


def health_snapshot() -> Dict[str, Any]:
    """Diagnostic data for `/health`: last ingest time, batch, and symbol count."""
    conn = get_conn()
    try:
        last = conn.execute(
            "SELECT received_at, batch_id FROM etf_ingest_log "
            "WHERE data_type != 'rate_limited' "
            "ORDER BY received_at DESC LIMIT 1"
        ).fetchone()
        # Count distinct symbols across all data tables.
        n = conn.execute(
            """
            SELECT COUNT(*) AS n FROM (
                SELECT DISTINCT symbol FROM etf_quote
                UNION SELECT DISTINCT symbol FROM etf_fundamentals
                UNION SELECT DISTINCT symbol FROM etf_holdings
                UNION SELECT DISTINCT symbol FROM etf_sector_weights
                UNION SELECT DISTINCT symbol FROM etf_performance
                UNION SELECT DISTINCT symbol FROM etf_equity_holdings
                UNION SELECT DISTINCT symbol FROM etf_esg
                UNION SELECT DISTINCT symbol FROM etf_news
            )
            """
        ).fetchone()["n"]
        return {
            "last_ingest_at": last["received_at"] if last else None,
            "last_batch_id": last["batch_id"] if last else None,
            "symbols_covered": n,
        }
    finally:
        conn.close()


def _get_payload_row(
    table: str, symbol: str, array_field: str
) -> Optional[Dict[str, Any]]:
    """Read a (symbol, as_of_date) PK row and rehydrate the JSON column."""
    conn = get_conn()
    try:
        row = conn.execute(
            f"SELECT as_of_date, payload_json FROM {table} "
            "WHERE symbol = ? ORDER BY as_of_date DESC LIMIT 1",
            (symbol,),
        ).fetchone()
        if not row:
            return None
        items = json.loads(row["payload_json"]) if row["payload_json"] else []
        return {
            "symbol": symbol,
            "as_of_date": row["as_of_date"],
            array_field: items,
        }
    finally:
        conn.close()
