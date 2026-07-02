"""HMAC auth middleware tests.

Covers the scenarios from `etf-ingest-auth` spec: valid sig, missing sig,
tampered body, stale / future timestamp, scope (read endpoints + /health
are NOT protected), and constant-time comparison.
"""
from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.middleware.hmac_auth import (
    HmacAuthMiddleware,
    verify_signature,
    verify_timestamp,
)
from backend.services.etf_config import reset_for_test


SECRET = "x" * 32


@pytest.fixture(autouse=True)
def configure(monkeypatch):
    monkeypatch.setenv("ETF_PIPELINE_SECRET", SECRET)
    monkeypatch.setenv("TIME_WINDOW_SECONDS", "300")
    reset_for_test()
    yield
    reset_for_test()


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(HmacAuthMiddleware)

    @app.post("/api/etf/ingest")
    async def ingest():
        return {"ok": True}

    @app.get("/api/etf/quote/QQQ")
    async def quote():
        return {"symbol": "QQQ", "quotes": []}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/docs")
    async def docs():
        return {}

    return app


def _sign(timestamp: str, body: bytes, secret: str = SECRET) -> str:
    msg = timestamp.encode("utf-8") + b"\n" + body
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_valid_signature_passes():
    client = TestClient(_make_app())
    body = b'{"data_type":"etf_quote","batch_id":"b","records":[]}'
    ts = _now_iso()
    r = client.post(
        "/api/etf/ingest",
        content=body,
        headers={
            "X-ETF-Pipeline-Timestamp": ts,
            "X-ETF-Pipeline-Signature": _sign(ts, body),
        },
    )
    assert r.status_code == 200


def test_missing_signature_header_rejected():
    client = TestClient(_make_app())
    body = b'{"x":1}'
    r = client.post(
        "/api/etf/ingest",
        content=body,
        headers={"X-ETF-Pipeline-Timestamp": _now_iso()},
    )
    assert r.status_code == 401
    assert r.json() == {"detail": "unauthorized"}


def test_missing_timestamp_header_rejected():
    client = TestClient(_make_app())
    r = client.post(
        "/api/etf/ingest",
        content=b'{"x":1}',
        headers={"X-ETF-Pipeline-Signature": "deadbeef"},
    )
    assert r.status_code == 401


def test_tampered_body_rejected():
    client = TestClient(_make_app())
    body = b'{"data_type":"etf_quote","batch_id":"b","records":[]}'
    ts = _now_iso()
    sig = _sign(ts, body)
    tampered = body + b" "
    r = client.post(
        "/api/etf/ingest",
        content=tampered,
        headers={
            "X-ETF-Pipeline-Timestamp": ts,
            "X-ETF-Pipeline-Signature": sig,
        },
    )
    assert r.status_code == 401


def test_stale_timestamp_rejected():
    client = TestClient(_make_app())
    body = b'{"x":1}'
    stale = datetime.now(timezone.utc).timestamp() - 600  # 10 min ago
    ts = datetime.fromtimestamp(stale, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = client.post(
        "/api/etf/ingest",
        content=body,
        headers={
            "X-ETF-Pipeline-Timestamp": ts,
            "X-ETF-Pipeline-Signature": _sign(ts, body),
        },
    )
    assert r.status_code == 401


def test_future_timestamp_rejected():
    client = TestClient(_make_app())
    body = b'{"x":1}'
    future = datetime.now(timezone.utc).timestamp() + 600
    ts = datetime.fromtimestamp(future, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = client.post(
        "/api/etf/ingest",
        content=body,
        headers={
            "X-ETF-Pipeline-Timestamp": ts,
            "X-ETF-Pipeline-Signature": _sign(ts, body),
        },
    )
    assert r.status_code == 401


def test_wrong_secret_rejected():
    client = TestClient(_make_app())
    body = b'{"x":1}'
    ts = _now_iso()
    r = client.post(
        "/api/etf/ingest",
        content=body,
        headers={
            "X-ETF-Pipeline-Timestamp": ts,
            "X-ETF-Pipeline-Signature": _sign(ts, body, secret="wrong" * 8),
        },
    )
    assert r.status_code == 401


def test_read_endpoint_not_protected():
    client = TestClient(_make_app())
    r = client.get("/api/etf/quote/QQQ")
    assert r.status_code == 200


def test_health_not_protected():
    client = TestClient(_make_app())
    r = client.get("/health")
    assert r.status_code == 200


def test_docs_not_protected():
    client = TestClient(_make_app())
    r = client.get("/docs")
    assert r.status_code == 200


def test_verify_signature_uses_constant_time():
    """Two same-length signatures must not short-circuit via `==`."""
    body = b'{"x":1}'
    ts = _now_iso()
    good = _sign(ts, body)
    bad = "0" * len(good)
    assert verify_signature(SECRET, ts, body, good) is True
    assert verify_signature(SECRET, ts, body, bad) is False


def test_verify_timestamp_window():
    assert verify_timestamp(_now_iso(), 300) is True
    stale = datetime.now(timezone.utc).timestamp() - 1000
    stale_ts = datetime.fromtimestamp(stale, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert verify_timestamp(stale_ts, 300) is False
    assert verify_timestamp("not-a-timestamp", 300) is False
    assert verify_timestamp("", 300) is False
