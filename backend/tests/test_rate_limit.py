"""Rate limit middleware tests.

Covers: under limit, at limit, per-IP buckets, read endpoints not limited,
429 writes to etf_ingest_log, restart preserves state, X-Forwarded-For
parsing.
"""
from __future__ import annotations

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.middleware.rate_limit import (
    RateLimitMiddleware,
    _reset_for_test,
    get_source_ip,
    start_flusher,
    stop_flusher,
)
from backend.services.etf_config import reset_for_test
from backend.services.etf_db import get_conn, init as init_etf_db


SECRET = "x" * 32


@pytest.fixture(autouse=True)
def configure(monkeypatch, tmp_path):
    db_path = tmp_path / "etf_remote.db"
    monkeypatch.setenv("ETF_PIPELINE_SECRET", SECRET)
    monkeypatch.setenv("REMOTE_DB_PATH", str(db_path))
    monkeypatch.setenv("INGEST_MAX_REQUESTS_PER_DAY", "2")
    monkeypatch.setenv("RATE_LIMIT_FLUSH_SECONDS", "1")
    init_etf_db()
    reset_for_test()
    _reset_for_test()
    yield
    stop_flusher()
    _reset_for_test()
    reset_for_test()


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.post("/api/etf/ingest")
    async def ingest():
        return {"ok": True}

    @app.get("/api/etf/quote/QQQ")
    async def quote():
        return {"symbol": "QQQ", "quotes": []}

    return app


def test_under_limit_allows():
    client = TestClient(_make_app())
    r1 = client.post("/api/etf/ingest", headers={"X-Forwarded-For": "1.2.3.4"})
    r2 = client.post("/api/etf/ingest", headers={"X-Forwarded-For": "1.2.3.4"})
    assert r1.status_code == 200
    assert r2.status_code == 200


def test_at_limit_blocks():
    client = TestClient(_make_app())
    client.post("/api/etf/ingest", headers={"X-Forwarded-For": "1.2.3.4"})
    client.post("/api/etf/ingest", headers={"X-Forwarded-For": "1.2.3.4"})
    r3 = client.post("/api/etf/ingest", headers={"X-Forwarded-For": "1.2.3.4"})
    assert r3.status_code == 429
    assert r3.json() == {"detail": "rate limit exceeded"}


def test_separate_ips_have_separate_buckets():
    client = TestClient(_make_app())
    assert client.post("/api/etf/ingest", headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 200
    assert client.post("/api/etf/ingest", headers={"X-Forwarded-For": "1.2.3.4"}).status_code == 200
    # Different IP — fresh bucket.
    assert client.post("/api/etf/ingest", headers={"X-Forwarded-For": "5.6.7.8"}).status_code == 200


def test_read_endpoint_not_rate_limited():
    client = TestClient(_make_app())
    for _ in range(10):
        assert client.get("/api/etf/quote/QQQ").status_code == 200


def test_429_writes_ingest_log():
    client = TestClient(_make_app())
    client.post("/api/etf/ingest", headers={"X-Forwarded-For": "1.2.3.4"})
    client.post("/api/etf/ingest", headers={"X-Forwarded-For": "1.2.3.4"})
    client.post("/api/etf/ingest", headers={"X-Forwarded-For": "1.2.3.4"})
    conn = get_conn()
    rows = conn.execute("SELECT * FROM etf_ingest_log").fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0]["data_type"] == "rate_limited"
    assert rows[0]["source_ip"] == "1.2.3.4"


def test_restart_preserves_state():
    # First "process": consume the bucket for one IP.
    client1 = TestClient(_make_app())
    client1.post("/api/etf/ingest", headers={"X-Forwarded-For": "1.2.3.4"})
    client1.post("/api/etf/ingest", headers={"X-Forwarded-For": "1.2.3.4"})
    # Persist state via the flusher.
    start_flusher()
    time.sleep(2)
    stop_flusher()
    # Simulate restart: clear in-memory state.
    _reset_for_test()
    client2 = TestClient(_make_app())
    # Third request — should still be 429 because state survived in sqlite.
    r = client2.post("/api/etf/ingest", headers={"X-Forwarded-For": "1.2.3.4"})
    assert r.status_code == 429


def test_x_forwarded_for_first_segment_used():
    class FakeReq:
        headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8, 9.10.11.12"}
        client = type("C", (), {"host": "127.0.0.1"})()

    assert get_source_ip(FakeReq()) == "1.2.3.4"


def test_falls_back_to_socket_when_no_xff():
    class FakeReq:
        headers = {}
        client = type("C", (), {"host": "127.0.0.1"})()

    assert get_source_ip(FakeReq()) == "127.0.0.1"
