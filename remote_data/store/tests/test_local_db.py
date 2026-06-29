"""Unit tests for remote_data.store.local_db."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from remote_data.store import local_db


@pytest.fixture()
def db(tmp_path):
    path = tmp_path / "test.db"
    local_db.init(path)
    conn = local_db.connect(path)
    yield conn
    conn.close()


def test_init_is_idempotent(tmp_path):
    path = tmp_path / "test.db"
    local_db.init(path)
    local_db.init(path)  # second call should be a no-op, no exception
    assert path.exists()


def test_init_creates_parent_dir(tmp_path):
    path = tmp_path / "nested" / "dir" / "test.db"
    local_db.init(path)
    assert path.exists()


def test_all_required_tables_exist(db):
    expected = {
        "etf_quote", "etf_fundamentals", "etf_holdings", "etf_sector_weights",
        "etf_performance", "etf_equity_holdings", "etf_esg", "etf_news",
        "etf_dead_letter", "fetch_log", "push_log",
    }
    assert expected.issubset(set(local_db.list_tables(db)))


def test_insert_quote_and_fetch_pending(db):
    local_db.insert_etf_quote(db, [
        {"symbol": "QQQ", "ts": "2026-06-29T13:30:00Z", "price": 521.34, "volume": 1000},
        {"symbol": "SPY", "ts": "2026-06-29T13:30:00Z", "price": 555.0, "volume": 2000},
    ])
    pending = local_db.fetch_pending(db, "etf_quote", limit=10)
    assert len(pending) == 2
    assert {r["symbol"] for r in pending} == {"QQQ", "SPY"}


def test_upsert_resets_pushed_at(db):
    local_db.insert_etf_quote(db, [{"symbol": "QQQ", "ts": "2026-06-29T13:30:00Z", "price": 100.0}])
    pending = local_db.fetch_pending(db, "etf_quote", limit=10)
    local_db.mark_pushed(db, "etf_quote", [r["id"] for r in pending])

    # Re-inserting same (symbol, ts) should reset pushed_at.
    local_db.insert_etf_quote(db, [{"symbol": "QQQ", "ts": "2026-06-29T13:30:00Z", "price": 101.0}])
    pending = local_db.fetch_pending(db, "etf_quote", limit=10)
    assert len(pending) == 1
    assert pending[0]["price"] == 101.0


def test_mark_pushed_clears_failed_at(db):
    local_db.insert_etf_quote(db, [{"symbol": "QQQ", "ts": "2026-06-29T13:30:00Z", "price": 1.0}])
    pending = local_db.fetch_pending(db, "etf_quote", limit=1)
    ids = [pending[0]["id"]]
    local_db.mark_failed(db, "etf_quote", ids, "boom")
    # failed rows excluded from pending.
    assert local_db.fetch_pending(db, "etf_quote", limit=10) == []
    # mark_pushed should resurrect them (failed_at -> NULL).
    local_db.mark_pushed(db, "etf_quote", ids)
    pending = local_db.fetch_pending(db, "etf_quote", limit=10)
    assert len(pending) == 0  # already pushed
    row = db.execute("SELECT pushed_at, failed_at FROM etf_quote WHERE id=?", ids).fetchone()
    assert row["pushed_at"] is not None
    assert row["failed_at"] is None


def test_mark_pushed_no_rows_when_empty(db):
    assert local_db.mark_pushed(db, "etf_quote", []) == 0


def test_dead_letter_writes_payload_and_marks_failed(db):
    local_db.insert_etf_quote(db, [
        {"symbol": "QQQ", "ts": "2026-06-29T13:30:00Z", "price": 1.0},
    ])
    pending = local_db.fetch_pending(db, "etf_quote", limit=1)
    ids = [pending[0]["id"]]
    local_db.write_dead_letter(
        db,
        data_type="etf_quote",
        source_ids=ids,
        batch_id="batch-1",
        response_status=400,
        response_body="bad schema",
    )
    dl = db.execute("SELECT * FROM etf_dead_letter").fetchall()
    assert len(dl) == 1
    assert dl[0]["data_type"] == "etf_quote"
    assert dl[0]["response_status"] == 400
    payload = json.loads(dl[0]["payload_json"])
    assert payload["symbol"] == "QQQ"
    row = db.execute("SELECT failed_at FROM etf_quote WHERE id=?", ids).fetchone()
    assert row["failed_at"] is not None


def test_prune_deletes_old_quote_rows(db):
    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(days=100)).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_ts = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    local_db.insert_etf_quote(db, [
        {"symbol": "QQQ", "ts": old_ts, "price": 1.0},
        {"symbol": "QQQ", "ts": new_ts, "price": 2.0},
    ])
    counts = local_db.prune(db, now=now)
    assert counts["etf_quote"] == 1
    remaining = db.execute("SELECT symbol FROM etf_quote").fetchall()
    assert len(remaining) == 1
    assert remaining[0]["symbol"] == "QQQ"


def test_prune_deletes_old_news_and_push_log(db):
    now = datetime.now(timezone.utc)
    old = (now - timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%SZ")
    new = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    local_db.insert_etf_news(db, [
        {"url": "u1", "symbol": "QQQ", "title": "old", "published_at": old, "publisher": "x", "summary": ""},
        {"url": "u2", "symbol": "QQQ", "title": "new", "published_at": new, "publisher": "x", "summary": ""},
    ])
    local_db.record_push_attempt(
        db, data_type="etf_quote", batch_id="b", http_status=200, retry_count=0, error=None, row_count=1
    )
    # Backdate push_log row by direct UPDATE so prune picks it up.
    db.execute(
        "UPDATE push_log SET sent_at=? WHERE data_type='etf_quote'",
        ((now - timedelta(days=40)).strftime("%Y-%m-%dT%H:%M:%SZ"),),
    )
    counts = local_db.prune(db, now=now)
    assert counts["etf_news"] == 1
    assert counts["push_log"] == 1


def test_record_fetch_and_push_attempt(db):
    rid = local_db.record_fetch(
        db, data_type="etf_quote", symbol="QQQ", status="ok", error=None, row_count=1
    )
    assert rid > 0
    pid = local_db.record_push_attempt(
        db, data_type="etf_quote", batch_id="b1", http_status=200, retry_count=0, error=None, row_count=5
    )
    assert pid > 0


def test_insert_required_field_missing_raises(db):
    with pytest.raises(ValueError):
        local_db.insert_etf_quote(db, [{"ts": "2026-06-29T13:30:00Z"}])  # missing symbol


def test_insert_unknown_data_type_raises(db):
    with pytest.raises(ValueError):
        local_db.fetch_pending(db, "etf_nonexistent", limit=1)