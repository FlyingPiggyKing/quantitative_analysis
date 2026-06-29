"""SQLite store for the overseas pipeline.

Contract: see openspec/changes/etf-fetcher-pusher/specs/etf-local-store/spec.md

Public surface:
    init(db_path=None)            # idempotent: creates parent dir + applies schema
    connect(db_path=None)         # returns a sqlite3.Connection
    insert_<data_type>(records)   # per data_type
    fetch_pending(data_type, limit)
    mark_pushed(data_type, ids)
    mark_failed(data_type, id, error)
    record_push_attempt(...)
    write_dead_letter(...)
    prune(now_iso=None)
    record_fetch(...)
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Mapping, Optional, Sequence

from remote_data.config import Config, load_config, resolve_db_path

logger = logging.getLogger(__name__)

_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_SCHEMA_FILE = _PACKAGE_DIR / "store" / "schema.sql"

# Retention (in days). Per design doc §3 / etf-local-store spec §"Retention".
RETENTION_DAYS = {
    "etf_quote": 90,
    "etf_news": 30,
    "push_log": 30,
}

# Column ordering per data_type — keeps insert_<X> from building SQL by hand.
_COLUMNS: Mapping[str, Sequence[str]] = {
    "etf_quote": (
        "symbol", "ts", "price", "pre_market_price", "post_market_price", "volume",
    ),
    "etf_fundamentals": (
        "symbol", "as_of", "pe", "pb", "dividend_yield", "dividend_rate",
    ),
    "etf_holdings": ("symbol", "as_of_date", "payload_json"),
    "etf_sector_weights": ("symbol", "as_of_date", "payload_json"),
    "etf_performance": (
        "symbol", "as_of_date", "ytd_return", "return_1y", "return_3y",
        "return_5y", "return_10y",
    ),
    "etf_equity_holdings": ("symbol", "as_of_date", "payload_json"),
    "etf_esg": (
        "symbol", "as_of_date", "total_esg", "environment", "social", "governance",
    ),
    "etf_news": (
        "url", "symbol", "title", "publisher", "published_at", "summary",
    ),
}

# Tables that store their JSON payload as a string (not normalized columns).
_JSON_PAYLOAD_TABLES = {"etf_holdings", "etf_sector_weights", "etf_equity_holdings"}

# Map logical "as_of" / "as_of_date" / "ts" / "published_at" fields to a
# column name and the dedup-key tuple in the schema.
_DEDUP_KEYS: Mapping[str, Sequence[str]] = {
    "etf_quote": ("symbol", "ts"),
    "etf_fundamentals": ("symbol", "as_of"),
    "etf_holdings": ("symbol", "as_of_date"),
    "etf_sector_weights": ("symbol", "as_of_date"),
    "etf_performance": ("symbol", "as_of_date"),
    "etf_equity_holdings": ("symbol", "as_of_date"),
    "etf_esg": ("symbol", "as_of_date"),
    "etf_news": ("url",),
}


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _default_db_path() -> Path:
    try:
        cfg = load_config()
        return resolve_db_path(cfg)
    except Exception:
        # Config might not be loadable (e.g. during ad-hoc init with no .env).
        # Fall back to the package-relative default.
        return (_PACKAGE_DIR / "data" / "etf_local.db").resolve()


# ---------------------------------------------------------------------------
# Connection / init
# ---------------------------------------------------------------------------


def _resolve_path(db_path: Optional[Path | str]) -> Path:
    if db_path is None:
        return _default_db_path()
    p = Path(db_path)
    return p if p.is_absolute() else (_PACKAGE_DIR / p).resolve()


def init(db_path: Optional[Path | str] = None, cfg: Optional[Config] = None) -> Path:
    """Idempotent: create parent dir + apply schema. Returns the resolved DB path.

    Safe to call on:
      - fresh filesystem (creates everything)
      - fully-initialized DB (no-op)
      - partial DB (creates missing tables/indexes)
    """
    path = _resolve_path(db_path or (resolve_db_path(cfg) if cfg else None))
    path.parent.mkdir(parents=True, exist_ok=True)
    sql = _SCHEMA_FILE.read_text(encoding="utf-8")

    with sqlite3.connect(path) as conn:
        conn.executescript(sql)
        conn.commit()
    logger.info("local_db.init: schema applied at %s", path)
    return path


def connect(db_path: Optional[Path | str] = None) -> sqlite3.Connection:
    """Open a connection. Caller manages lifecycle (use as context manager)."""
    path = _resolve_path(db_path)
    conn = sqlite3.connect(path, isolation_level=None)  # autocommit; we manage txns
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    conn.execute("BEGIN")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


# ---------------------------------------------------------------------------
# Inserts
# ---------------------------------------------------------------------------


def _row_to_values(table: str, record: Mapping[str, Any]) -> tuple:
    cols = _COLUMNS[table]
    out = []
    for c in cols:
        v = record.get(c)
        if v is None and c in ("symbol", "ts", "as_of", "as_of_date", "published_at", "url"):
            raise ValueError(f"{table} record missing required field {c}: {record!r}")
        if c == "payload_json" and v is not None and not isinstance(v, str):
            v = json.dumps(v, ensure_ascii=False, sort_keys=True)
        out.append(v)
    return tuple(out)


def _insert_records(conn: sqlite3.Connection, table: str, records: Sequence[Mapping[str, Any]]) -> int:
    """UPSERT-style insert: duplicate (dedup-key) rows have pushed_at reset so the
    newer record becomes eligible for pushing again.
    """
    if not records:
        return 0
    cols = _COLUMNS[table]
    placeholders = ",".join("?" * len(cols))
    col_list = ",".join(cols)
    conflict_cols = ",".join(_DEDUP_KEYS[table])
    update_cols = ",".join(f"{c}=excluded.{c}" for c in cols if c not in _DEDUP_KEYS[table])
    sql = (
        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
        f"ON CONFLICT({conflict_cols}) DO UPDATE SET "
        f"{update_cols}, pushed_at=NULL, failed_at=NULL"
    )
    rows = [_row_to_values(table, r) for r in records]
    with transaction(conn):
        conn.executemany(sql, rows)
    return len(rows)


def insert_etf_quote(conn: sqlite3.Connection, records: Sequence[Mapping[str, Any]]) -> int:
    return _insert_records(conn, "etf_quote", records)


def insert_etf_fundamentals(conn: sqlite3.Connection, records: Sequence[Mapping[str, Any]]) -> int:
    return _insert_records(conn, "etf_fundamentals", records)


def insert_etf_holdings(conn: sqlite3.Connection, records: Sequence[Mapping[str, Any]]) -> int:
    return _insert_records(conn, "etf_holdings", records)


def insert_etf_sector_weights(conn: sqlite3.Connection, records: Sequence[Mapping[str, Any]]) -> int:
    return _insert_records(conn, "etf_sector_weights", records)


def insert_etf_performance(conn: sqlite3.Connection, records: Sequence[Mapping[str, Any]]) -> int:
    return _insert_records(conn, "etf_performance", records)


def insert_etf_equity_holdings(conn: sqlite3.Connection, records: Sequence[Mapping[str, Any]]) -> int:
    return _insert_records(conn, "etf_equity_holdings", records)


def insert_etf_esg(conn: sqlite3.Connection, records: Sequence[Mapping[str, Any]]) -> int:
    return _insert_records(conn, "etf_esg", records)


def insert_etf_news(conn: sqlite3.Connection, records: Sequence[Mapping[str, Any]]) -> int:
    return _insert_records(conn, "etf_news", records)


# ---------------------------------------------------------------------------
# Push cursor + audit
# ---------------------------------------------------------------------------


_ORDER_COL: Mapping[str, str] = {
    "etf_quote": "ts",
    "etf_fundamentals": "as_of",
    "etf_holdings": "as_of_date",
    "etf_sector_weights": "as_of_date",
    "etf_performance": "as_of_date",
    "etf_equity_holdings": "as_of_date",
    "etf_esg": "as_of_date",
    "etf_news": "published_at",
}


def fetch_pending(conn: sqlite3.Connection, data_type: str, limit: int = 100) -> List[sqlite3.Row]:
    if data_type not in _COLUMNS:
        raise ValueError(f"Unknown data_type {data_type!r}")
    order_col = _ORDER_COL[data_type]
    sql = (
        f"SELECT * FROM {data_type} "
        f"WHERE pushed_at IS NULL AND failed_at IS NULL "
        f"ORDER BY {order_col} ASC LIMIT ?"
    )
    return list(conn.execute(sql, (limit,)))


def mark_pushed(conn: sqlite3.Connection, data_type: str, ids: Sequence[int]) -> int:
    if not ids:
        return 0
    placeholders = ",".join("?" * len(ids))
    sql = f"UPDATE {data_type} SET pushed_at = ?, failed_at = NULL WHERE id IN ({placeholders})"
    with transaction(conn):
        cur = conn.execute(sql, [_now_utc_iso(), *ids])
    return cur.rowcount or 0


def mark_failed(conn: sqlite3.Connection, data_type: str, ids: Sequence[int], error: str) -> int:
    """Mark rows as dead-lettered locally (failed_at set). The caller still needs
    to call `write_dead_letter` to capture the full payload + response body."""
    if not ids:
        return 0
    placeholders = ",".join("?" * len(ids))
    sql = f"UPDATE {data_type} SET failed_at = ? WHERE id IN ({placeholders})"
    with transaction(conn):
        cur = conn.execute(sql, [_now_utc_iso(), *ids])
    return cur.rowcount or 0


def record_push_attempt(
    conn: sqlite3.Connection,
    *,
    data_type: str,
    batch_id: Optional[str],
    http_status: Optional[int],
    retry_count: int,
    error: Optional[str],
    row_count: int,
) -> int:
    sql = (
        "INSERT INTO push_log (sent_at, data_type, batch_id, http_status, "
        "retry_count, error, row_count) VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
    with transaction(conn):
        cur = conn.execute(
            sql,
            (_now_utc_iso(), data_type, batch_id, http_status, retry_count, error, row_count),
        )
    return cur.lastrowid or 0


def record_fetch(
    conn: sqlite3.Connection,
    *,
    data_type: str,
    symbol: Optional[str],
    status: str,
    error: Optional[str],
    row_count: Optional[int],
) -> int:
    sql = (
        "INSERT INTO fetch_log (ts, data_type, symbol, status, error, row_count) "
        "VALUES (?, ?, ?, ?, ?, ?)"
    )
    with transaction(conn):
        cur = conn.execute(
            sql,
            (_now_utc_iso(), data_type, symbol, status, error, row_count),
        )
    return cur.lastrowid or 0


def write_dead_letter(
    conn: sqlite3.Connection,
    *,
    data_type: str,
    source_ids: Sequence[int],
    batch_id: Optional[str],
    response_status: Optional[int],
    response_body: Optional[str],
) -> int:
    """Snapshot the failing rows' payload into `etf_dead_letter` and set their
    `failed_at`. `payload_json` is reconstructed from the business table."""
    if not source_ids:
        return 0
    placeholders = ",".join("?" * len(source_ids))
    select_sql = f"SELECT * FROM {data_type} WHERE id IN ({placeholders})"
    rows = list(conn.execute(select_sql, source_ids))
    if not rows:
        return 0

    payloads = []
    for r in rows:
        rec = dict(r)
        if data_type in _JSON_PAYLOAD_TABLES:
            try:
                rec["payload_json"] = json.loads(rec["payload_json"])
            except Exception:
                pass
        payloads.append(json.dumps(rec, ensure_ascii=False, sort_keys=True, default=str))

    insert_sql = (
        "INSERT INTO etf_dead_letter (dead_lettered_at, data_type, source_id, "
        "batch_id, payload_json, response_status, response_body) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)"
    )
    ts = _now_utc_iso()
    placeholders = ",".join("?" * len(source_ids))
    update_sql = f"UPDATE {data_type} SET failed_at = ? WHERE id IN ({placeholders})"
    err = response_body or f"status={response_status}"

    with transaction(conn):
        for sid, p in zip(source_ids, payloads):
            conn.execute(
                insert_sql,
                (ts, data_type, sid, batch_id, p, response_status, response_body),
            )
        conn.execute(update_sql, [ts, *source_ids])
    # Mirror to fetch_log so ops can see why a record was dropped.
    for sid in source_ids:
        record_fetch(
            conn, data_type=data_type, symbol=None, status="dead_letter",
            error=err, row_count=None,
        )
    return len(rows)


# ---------------------------------------------------------------------------
# Maintenance
# ---------------------------------------------------------------------------


def prune(conn: sqlite3.Connection, *, now: Optional[datetime] = None) -> dict[str, int]:
    """Delete old rows per retention thresholds. Returns per-table counts."""
    now = now or datetime.now(timezone.utc)
    counts: dict[str, int] = {}
    for table, days in RETENTION_DAYS.items():
        ts_col = "published_at" if table == "etf_news" else (
            "ts" if table == "etf_quote" else "sent_at"
        )
        cutoff = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        sql = f"DELETE FROM {table} WHERE {ts_col} < ?"
        with transaction(conn):
            cur = conn.execute(sql, (cutoff,))
        counts[table] = cur.rowcount or 0
    return counts


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    )
    return cur.fetchone() is not None


def list_tables(conn: sqlite3.Connection) -> List[str]:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return [r[0] for r in cur.fetchall()]


def all_business_tables() -> Iterable[str]:
    return _COLUMNS.keys()


__all__ = [
    "init",
    "connect",
    "transaction",
    "fetch_pending",
    "mark_pushed",
    "mark_failed",
    "record_push_attempt",
    "record_fetch",
    "write_dead_letter",
    "prune",
    "table_exists",
    "list_tables",
    "all_business_tables",
    "insert_etf_quote",
    "insert_etf_fundamentals",
    "insert_etf_holdings",
    "insert_etf_sector_weights",
    "insert_etf_performance",
    "insert_etf_equity_holdings",
    "insert_etf_esg",
    "insert_etf_news",
]