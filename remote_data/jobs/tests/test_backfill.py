"""Backfill tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from remote_data.config import Config


def _cfg(tmp_path: Path) -> Config:
    return Config(
        deploy_role="LOCAL",
        remote_ingest_url="https://example.com/ingest",
        etf_pipeline_secret="x" * 32,
        local_db_path=str(tmp_path / "db.sqlite"),
        time_window_seconds=300,
        http_timeout_seconds=15,
        yahooquery_max_retries=1,
        yahooquery_backoff_seconds=0,
        symbols=["QQQ"],
        fetch_quotes_interval_minutes=5,
        fetch_quotes_offhours_interval_minutes=30,
        push_interval_seconds=30,
        batch_size=500,
        market_tz="US/Eastern",
        log_level="INFO",
        log_file=str(tmp_path / "log.txt"),
    )


def test_backfill_populates_empty_db(tmp_path, monkeypatch):
    from remote_data.store import local_db
    from remote_data.jobs import backfill_fundamentals as bf

    db_path = tmp_path / "db.sqlite"
    local_db.init(db_path)
    conn = local_db.connect(db_path)
    cfg = _cfg(tmp_path)

    # Patch fetch_fundamentals to return canned data so we don't hit yahooquery.
    monkeypatch.setattr(
        bf, "fetch_fundamentals",
        lambda symbols: [
            {"symbol": s, "as_of": "2026-06-29T20:00:00Z", "pe": 25.0, "pb": 5.0,
             "dividend_yield": 0.01, "dividend_rate": 1.0}
            for s in symbols
        ],
    )

    inserted = bf.run_once(conn, cfg)
    assert inserted == 1
    rows = conn.execute("SELECT * FROM etf_fundamentals").fetchall()
    assert len(rows) == 1
    assert rows[0]["symbol"] == "QQQ"

    log = conn.execute(
        "SELECT * FROM fetch_log WHERE data_type='etf_fundamentals'"
    ).fetchall()
    assert any(r["status"] == "ok" and r["row_count"] == 1 for r in log)
    conn.close()


def test_backfill_skips_non_empty_db(tmp_path, monkeypatch):
    from remote_data.store import local_db
    from remote_data.jobs import backfill_fundamentals as bf

    db_path = tmp_path / "db.sqlite"
    local_db.init(db_path)
    conn = local_db.connect(db_path)
    cfg = _cfg(tmp_path)

    # Pre-populate.
    local_db.insert_etf_fundamentals(conn, [{
        "symbol": "QQQ", "as_of": "2026-06-29T20:00:00Z", "pe": 1.0, "pb": 1.0,
        "dividend_yield": 0.0, "dividend_rate": 0.0,
    }])

    called = {"value": False}
    def fake_fetch(symbols):
        called["value"] = True
        return []

    monkeypatch.setattr(bf, "fetch_fundamentals", fake_fetch)
    inserted = bf.run_once(conn, cfg)
    assert inserted == 0
    assert called["value"] is False
    conn.close()