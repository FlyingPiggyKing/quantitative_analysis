"""SQLite connection + schema bootstrap for the ETF remote ingest database.

The remote ingest database (`etf_remote.db`) is independent from `watchlist.db`
so the ETL path of the overseas pusher can't conflict with the watchlist app's
own migrations. Connections are opened per-call (sqlite3 connections aren't
safe to share across FastAPI's threadpool workers).
"""
import os
import sqlite3
from pathlib import Path

_SCHEMA_PATH = Path(__file__).parent.parent / "migrations" / "etf_schema.sql"
_DEFAULT_DB_PATH = "./data/etf_remote.db"


def _resolve_db_path() -> Path:
    """Resolve REMOTE_DB_PATH, anchoring relative paths at the backend/ dir.

    Anchoring at backend/ (where main.py lives) keeps the path stable regardless
    of the CWD the process is launched from — which is the convention the rest
    of this codebase follows (watchlist.db is also resolved relative to backend/).
    """
    raw = os.getenv("REMOTE_DB_PATH", _DEFAULT_DB_PATH)
    p = Path(raw)
    if not p.is_absolute():
        p = Path(__file__).parent.parent / p
    return p


def get_conn() -> sqlite3.Connection:
    """Open a fresh connection to the ETF remote database."""
    db_path = _resolve_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init() -> None:
    """Execute the schema file idempotently. Safe to call on every startup."""
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    conn = get_conn()
    try:
        conn.executescript(schema)
        conn.commit()
    finally:
        conn.close()
