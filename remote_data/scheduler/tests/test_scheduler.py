"""Scheduler resilience tests."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from remote_data.config import Config
from remote_data.scheduler.jobs import (
    build_scheduler,
    make_fetch_job,
    safe_run,
    market_status,
)


def _cfg(tmp_path) -> Config:
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
        fetch_news_interval_minutes=60,
        push_interval_seconds=30,
        batch_size=500,
        market_tz="US/Eastern",
        log_level="INFO",
        log_file=str(tmp_path / "log.txt"),
    )


def test_safe_run_writes_records(tmp_path):
    from remote_data.store import local_db
    db_path = tmp_path / "db.sqlite"
    local_db.init(db_path)
    conn = local_db.connect(db_path)

    def fetcher(symbols):
        return [{"symbol": s, "ts": "2026-06-29T13:30:00Z", "price": 1.0} for s in symbols]

    safe_run(
        conn, "etf_quote", fetcher, local_db.insert_etf_quote, symbols=["QQQ"],
    )
    pending = local_db.fetch_pending(conn, "etf_quote", limit=10)
    assert len(pending) == 1
    log_rows = conn.execute("SELECT * FROM fetch_log").fetchall()
    assert len(log_rows) == 1
    assert log_rows[0]["status"] == "ok"
    assert log_rows[0]["row_count"] == 1
    conn.close()


def test_safe_run_logs_but_does_not_raise(tmp_path):
    from remote_data.store import local_db
    db_path = tmp_path / "db.sqlite"
    local_db.init(db_path)
    conn = local_db.connect(db_path)

    def boom(_symbols):
        raise RuntimeError("kaboom")

    safe_run(
        conn, "etf_quote", boom, local_db.insert_etf_quote, symbols=["QQQ"],
    )
    log_rows = conn.execute("SELECT * FROM fetch_log").fetchall()
    assert len(log_rows) == 1
    assert log_rows[0]["status"] == "error"
    assert "kaboom" in log_rows[0]["error"]
    # No records inserted.
    assert local_db.fetch_pending(conn, "etf_quote", limit=10) == []
    conn.close()


def test_make_fetch_job_writes_records(tmp_path, monkeypatch):
    """make_fetch_job wraps safe_run — verified end-to-end with a passing fetcher."""
    from remote_data.store import local_db
    monkeypatch.setenv("DEPLOY_ROLE", "LOCAL")
    monkeypatch.setenv("REMOTE_INGEST_URL", "https://example.com/ingest")
    monkeypatch.setenv("ETF_PIPELINE_SECRET", "x" * 32)

    db_path = tmp_path / "db.sqlite"
    local_db.init(db_path)
    cfg = _cfg(tmp_path)

    def conn_factory():
        return local_db.connect(db_path)

    job = make_fetch_job(
        "etf_fundamentals", conn_factory=conn_factory, cfg=cfg,
    )

    # Patch the fetcher the job captured (closure reference) to return canned
    # data — verifies end-to-end integration with the store.
    from remote_data.fetcher import etf_fundamentals as fund_mod

    def fake_fetch(symbols):
        return [{"symbol": s, "as_of": "2026-06-29T20:00:00Z", "pe": 1.0, "pb": 1.0,
                 "dividend_yield": 0.0, "dividend_rate": 0.0} for s in symbols]

    fund_mod.fetch_fundamentals = fake_fetch
    job()

    conn = conn_factory()
    pending = local_db.fetch_pending(conn, "etf_fundamentals", limit=10)
    assert len(pending) == 1
    log_rows = conn.execute(
        "SELECT * FROM fetch_log WHERE data_type='etf_fundamentals'"
    ).fetchall()
    assert len(log_rows) == 1
    assert log_rows[0]["status"] == "ok"
    conn.close()


def test_market_status_open():
    from datetime import datetime, timezone
    # Tuesday 12:00 UTC = 08:00 ET (pre-market)
    assert market_status(datetime(2026, 6, 30, 12, 0, tzinfo=timezone.utc)) == "pre"
    # Tuesday 14:30 UTC = 10:30 ET (open)
    assert market_status(datetime(2026, 6, 30, 14, 30, tzinfo=timezone.utc)) == "open"
    # Tuesday 20:30 UTC = 16:30 ET (post)
    assert market_status(datetime(2026, 6, 30, 20, 30, tzinfo=timezone.utc)) == "post"
    # Sunday → closed
    assert market_status(datetime(2026, 6, 28, 18, 0, tzinfo=timezone.utc)) == "closed"


def test_build_scheduler_registers_all_jobs(tmp_path, monkeypatch):
    monkeypatch.setenv("DEPLOY_ROLE", "LOCAL")
    monkeypatch.setenv("REMOTE_INGEST_URL", "https://example.com/ingest")
    monkeypatch.setenv("ETF_PIPELINE_SECRET", "x" * 32)
    from remote_data.store import local_db
    db_path = tmp_path / "db.sqlite"
    local_db.init(db_path)
    cfg = _cfg(tmp_path)

    def conn_factory():
        return local_db.connect(db_path)

    scheduler = build_scheduler(cfg, conn_factory=conn_factory)
    job_ids = {j.id for j in scheduler.get_jobs()}
    expected = {
        "push_loop", "fetch_quotes_market", "fetch_news",
        "fetch_fundamentals", "fetch_performance",
        "fetch_holdings", "fetch_sector_weights",
        "fetch_equity_holdings", "fetch_esg", "prune",
    }
    assert expected.issubset(job_ids)