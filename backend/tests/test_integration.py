"""End-to-end integration tests for the ETF remote-data pipeline.

Covers tasks 10.3–10.10 from the change. The full change also calls for
starting the real `etf-fetcher-pusher` process (10.1, 10.2) and waiting a
full 5-minute quote tick (10.3) — those are exercised manually because they
require network access to yahooquery. Everything that can be tested with
FastAPI's TestClient is covered here.

The test mounts the SAME middleware stack the production app uses (HMAC +
rate-limit + the real router), so the request flow is identical to what
the pusher would see.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.etf_ingest import router as ingest_router
from backend.api.etf_read import router as read_router
from backend.middleware.hmac_auth import HmacAuthMiddleware
from backend.middleware.rate_limit import (
    RateLimitMiddleware,
    _reset_for_test,
    start_flusher,
    stop_flusher,
)
from backend.services.etf_config import reset_for_test
from backend.services.etf_db import get_conn, init as init_etf_db


SECRET = "integration-test-secret-" + "x" * 20


@pytest.fixture
def full_app(monkeypatch, tmp_path):
    """Build the real production app: CORS + HMAC + rate-limit + both routers."""
    db_path = tmp_path / "etf_remote.db"
    monkeypatch.setenv("ETF_PIPELINE_SECRET", SECRET)
    monkeypatch.setenv("REMOTE_DB_PATH", str(db_path))
    monkeypatch.setenv("TIME_WINDOW_SECONDS", "300")
    monkeypatch.setenv("INGEST_MAX_REQUESTS_PER_DAY", "50000")
    monkeypatch.setenv("INGEST_MAX_BODY_BYTES", "1048576")
    monkeypatch.setenv("RATE_LIMIT_FLUSH_SECONDS", "1")
    init_etf_db()
    reset_for_test()
    _reset_for_test()
    # Add middlewares in the same order as main.py: rate-limit first
    # (innermost), HMAC second (outermost) so 401s do not consume budget.
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(HmacAuthMiddleware)
    app.include_router(ingest_router)
    app.include_router(read_router)
    yield app
    stop_flusher()
    _reset_for_test()
    reset_for_test()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sign(timestamp: str, body: bytes) -> str:
    msg = timestamp.encode("utf-8") + b"\n" + body
    return hmac.new(SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def _post_quote(client: TestClient, symbol: str, ts: str, price: float):
    body = {
        "data_type": "etf_quote",
        "batch_id": f"batch-{ts}-{symbol}",
        "records": [{"symbol": symbol, "ts": ts, "price": price}],
    }
    raw = json.dumps(body, sort_keys=True).encode("utf-8")
    ts_header = _now_iso()
    return client.post(
        "/api/etf/ingest",
        content=raw,
        headers={
            "Content-Type": "application/json",
            "X-ETF-Pipeline-Timestamp": ts_header,
            "X-ETF-Pipeline-Signature": _sign(ts_header, raw),
        },
    )


def _row_count(table: str) -> int:
    conn = get_conn()
    try:
        return conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 10.3 + 10.4 — end-to-end push and read
# ---------------------------------------------------------------------------


def test_push_then_read_returns_data(full_app):
    """Push one quote via the real ingest path, then read it back."""
    client = TestClient(full_app)
    r = _post_quote(client, "QQQ", "2026-06-29T03:14:00Z", 100.0)
    assert r.status_code == 200
    assert r.json()["accepted"] == 1

    # Read API: newest first, single row.
    r = client.get("/api/etf/quote/QQQ")
    assert r.status_code == 200
    data = r.json()
    assert data["symbol"] == "QQQ"
    assert data["quotes"][0]["price"] == 100.0
    assert data["quotes"][0]["ts"] == "2026-06-29T03:14:00Z"

    # Ingest log got the audit row.
    assert _row_count("etf_ingest_log") == 1


# ---------------------------------------------------------------------------
# 10.5 — HMAC failure leaves no ingest log
# ---------------------------------------------------------------------------


def test_hmac_failure_returns_401_and_no_log(full_app):
    client = TestClient(full_app)
    raw = b'{"data_type":"etf_quote","batch_id":"b","records":[]}'
    r = client.post(
        "/api/etf/ingest",
        content=raw,
        headers={
            "X-ETF-Pipeline-Timestamp": _now_iso(),
            "X-ETF-Pipeline-Signature": "deadbeef" * 8,
        },
    )
    assert r.status_code == 401
    assert r.json() == {"detail": "unauthorized"}
    assert _row_count("etf_ingest_log") == 0


# ---------------------------------------------------------------------------
# 10.6 — Rate limit kicks in at the configured cap
# ---------------------------------------------------------------------------


def test_rate_limit_blocks_after_cap(monkeypatch, full_app, tmp_path):
    """Set INGEST_MAX_REQUESTS_PER_DAY=2, push 3 → first 2 succeed, third 429."""
    # Override the env and rebuild the app with the lower cap.
    monkeypatch.setenv("INGEST_MAX_REQUESTS_PER_DAY", "2")
    reset_for_test()
    _reset_for_test()
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(HmacAuthMiddleware)
    app.include_router(ingest_router)
    app.include_router(read_router)

    client = TestClient(app)
    r1 = _post_quote(client, "QQQ", "2026-06-29T03:14:00Z", 100.0)
    r2 = _post_quote(client, "QQQ", "2026-06-29T03:15:00Z", 101.0)
    r3 = _post_quote(client, "QQQ", "2026-06-29T03:16:00Z", 102.0)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.json() == {"detail": "rate limit exceeded"}

    # Only 2 etf_quote rows landed; the 3rd never reached the dispatcher.
    assert _row_count("etf_quote") == 2
    # etf_ingest_log has 2 accepted rows + 1 rate_limited row.
    conn = get_conn()
    try:
        log_rows = conn.execute("SELECT * FROM etf_ingest_log").fetchall()
    finally:
        conn.close()
    assert sum(1 for r in log_rows if r["data_type"] == "etf_quote") == 2
    assert sum(1 for r in log_rows if r["data_type"] == "rate_limited") == 1


# ---------------------------------------------------------------------------
# 10.7 — Rate-limit state survives a restart
# ---------------------------------------------------------------------------


def test_rate_limit_state_survives_restart(monkeypatch, tmp_path):
    """Push to consume 40000/50000, restart, push 10001 more → 429."""
    # First process: consume 1 request, persist state, shut down.
    monkeypatch.setenv("ETF_PIPELINE_SECRET", SECRET)
    monkeypatch.setenv("REMOTE_DB_PATH", str(tmp_path / "etf_remote.db"))
    monkeypatch.setenv("INGEST_MAX_REQUESTS_PER_DAY", "2")
    monkeypatch.setenv("RATE_LIMIT_FLUSH_SECONDS", "1")
    init_etf_db()
    reset_for_test()
    _reset_for_test()

    app1 = FastAPI()
    app1.add_middleware(RateLimitMiddleware)
    app1.add_middleware(HmacAuthMiddleware)
    app1.include_router(ingest_router)
    app1.include_router(read_router)
    client1 = TestClient(app1)

    # Consume 2/2 — the next request from the same IP will be 429.
    client1.post(
        "/api/etf/ingest",
        content=b'{"data_type":"etf_quote","batch_id":"b1","records":[]}',
        headers={
            "X-Forwarded-For": "10.0.0.1",
            "X-ETF-Pipeline-Timestamp": _now_iso(),
            "X-ETF-Pipeline-Signature": _sign(_now_iso(), b'{"data_type":"etf_quote","batch_id":"b1","records":[]}'),
        },
    )
    client1.post(
        "/api/etf/ingest",
        content=b'{"data_type":"etf_quote","batch_id":"b2","records":[]}',
        headers={
            "X-Forwarded-For": "10.0.0.1",
            "X-ETF-Pipeline-Timestamp": _now_iso(),
            "X-ETF-Pipeline-Signature": _sign(_now_iso(), b'{"data_type":"etf_quote","batch_id":"b2","records":[]}'),
        },
    )
    # Force a flush.
    start_flusher()
    time.sleep(2)
    stop_flusher()
    # And one explicit flush for determinism (don't depend on the thread
    # having run its loop before stop_flusher() observed the event).
    from backend.middleware.rate_limit import _flush
    _flush()

    # Restart: clear in-memory state.
    _reset_for_test()
    app2 = FastAPI()
    app2.add_middleware(RateLimitMiddleware)
    app2.add_middleware(HmacAuthMiddleware)
    app2.include_router(ingest_router)
    app2.include_router(read_router)
    client2 = TestClient(app2)

    # Same IP — should still be 429 because state was persisted.
    r = client2.post(
        "/api/etf/ingest",
        content=b'{"data_type":"etf_quote","batch_id":"b3","records":[]}',
        headers={
            "X-Forwarded-For": "10.0.0.1",
            "X-ETF-Pipeline-Timestamp": _now_iso(),
            "X-ETF-Pipeline-Signature": _sign(_now_iso(), b'{"data_type":"etf_quote","batch_id":"b3","records":[]}'),
        },
    )
    assert r.status_code == 429


# ---------------------------------------------------------------------------
# 10.8 — UPSERT dedupe on (symbol, ts)
# ---------------------------------------------------------------------------


def test_upsert_dedupe_same_symbol_ts(full_app):
    client = TestClient(full_app)
    _post_quote(client, "QQQ", "2026-06-29T03:14:00Z", 100.0)
    _post_quote(client, "QQQ", "2026-06-29T03:14:00Z", 999.0)  # same PK, new price
    assert _row_count("etf_quote") == 1
    r = client.get("/api/etf/quote/QQQ")
    assert r.json()["quotes"][0]["price"] == 999.0


# ---------------------------------------------------------------------------
# 10.9 — News dedupe on url
# ---------------------------------------------------------------------------


def test_news_dedupe_same_url(full_app):
    client = TestClient(full_app)
    body = {
        "data_type": "etf_news",
        "batch_id": "n1",
        "records": [
            {
                "url": "https://example.com/abc",
                "symbol": "QQQ",
                "title": "Original",
                "publisher": "P",
                "published_at": "2026-06-29T03:14:00Z",
                "summary": "S",
            }
        ],
    }
    raw = json.dumps(body, sort_keys=True).encode("utf-8")
    ts = _now_iso()
    client.post(
        "/api/etf/ingest",
        content=raw,
        headers={
            "X-ETF-Pipeline-Timestamp": ts,
            "X-ETF-Pipeline-Signature": _sign(ts, raw),
        },
    )
    # Second push with same url but different title — should be dropped.
    body["records"][0]["title"] = "Updated"
    raw2 = json.dumps(body, sort_keys=True).encode("utf-8")
    ts2 = _now_iso()
    r2 = client.post(
        "/api/etf/ingest",
        content=raw2,
        headers={
            "X-ETF-Pipeline-Timestamp": ts2,
            "X-ETF-Pipeline-Signature": _sign(ts2, raw2),
        },
    )
    # The 2nd push is accepted by the dispatcher (HTTP 200 because both
    # records "passed" validation) but `insert_news` is INSERT OR IGNORE,
    # so the row count is 1 and the original title is preserved.
    assert r2.status_code == 200
    assert _row_count("etf_news") == 1
    r = client.get("/api/etf/news/QQQ")
    assert r.json()["news"][0]["title"] == "Original"


# ---------------------------------------------------------------------------
# 10.10 — Partial success returns HTTP 207
# ---------------------------------------------------------------------------


def test_partial_success_returns_207(full_app):
    client = TestClient(full_app)
    body = {
        "data_type": "etf_quote",
        "batch_id": "partial",
        "records": [
            {"symbol": "QQQ", "ts": "2026-06-29T03:14:00Z", "price": 100.0},
            {"symbol": "SPY", "ts": "2026-06-29T03:14:00Z", "price": 200.0},
            # Missing `ts` — invalid.
            {"symbol": "AGG", "price": 50.0},
            {"symbol": "VTI", "ts": "2026-06-29T03:14:00Z", "price": 80.0},
            {"symbol": "IWM", "ts": "2026-06-29T03:14:00Z", "price": 70.0},
        ],
    }
    raw = json.dumps(body, sort_keys=True).encode("utf-8")
    ts = _now_iso()
    r = client.post(
        "/api/etf/ingest",
        content=raw,
        headers={
            "X-ETF-Pipeline-Timestamp": ts,
            "X-ETF-Pipeline-Signature": _sign(ts, raw),
        },
    )
    assert r.status_code == 207
    data = r.json()
    assert data["accepted"] == 4
    assert data["rejected"] == 1
    assert data["errors"][0]["index"] == 2
    assert _row_count("etf_quote") == 4
