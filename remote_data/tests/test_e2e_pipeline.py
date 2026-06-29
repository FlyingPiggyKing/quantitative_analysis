"""End-to-end pipeline tests (Phase 9).

Verifies the full fetcher → store → pusher → mock-ingest flow using
httpx.MockTransport (no real socket).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
import threading
import time
import types

import httpx
import pytest


# ---------------------------------------------------------------------------
# Fake yahooquery
# ---------------------------------------------------------------------------


def _install_fake_yahooquery():
    mod = types.ModuleType("yahooquery")

    class _FakeTicker:
        def __init__(self, symbol, **kwargs):
            self.symbol = symbol

        @property
        def price(self):
            return {self.symbol: {
                "regularMarketTime": int(time.time()),
                "regularMarketPrice": 521.34, "preMarketPrice": None,
                "postMarketPrice": None, "regularMarketVolume": 1000,
            }}

        @property
        def summary_detail(self):
            return {self.symbol: {"trailingPE": 25.0, "priceToBook": 5.0, "dividendYield": 0.01, "dividendRate": 1.0}}

        @property
        def key_stats(self):
            return {self.symbol: {}}

        @property
        def fund_holding_info(self):
            return {self.symbol: {"asOfDate": "2026-06-15", "holdings": {}}}

        @property
        def fund_sector_weightings(self):
            return {self.symbol: {"asOfDate": "2026-06-15"}}

        @property
        def fund_performance(self):
            return {self.symbol: {"asOfDate": "2026-06-15", "performanceOverview": {}}}

        @property
        def fund_esg_scores(self):
            return {self.symbol: {"asOfDate": "2026-06-01"}}

        @property
        def news(self):
            return []

    mod.Ticker = _FakeTicker
    sys.modules["yahooquery"] = mod


# ---------------------------------------------------------------------------
# Mock transport that records every request and returns canned responses.
# ---------------------------------------------------------------------------


class _MockTransport(httpx.MockTransport):
    def __init__(self):
        self.calls = []
        self.response_status = 200
        super().__init__(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.calls.append({
            "url": str(request.url),
            "body": request.content,
            "headers": dict(request.headers),
        })
        status = self.response_status
        if 200 <= status < 300:
            return httpx.Response(
                status_code=status,
                content=json.dumps({"accepted": 0, "rejected": 0, "batch_id": "ok"}).encode(),
                headers={"Content-Type": "application/json"},
            )
        return httpx.Response(
            status_code=status,
            content=json.dumps({"detail": "mock error"}).encode(),
            headers={"Content-Type": "application/json"},
        )


def _env_setup(monkeypatch, tmp_path):
    monkeypatch.setenv("DEPLOY_ROLE", "LOCAL")
    monkeypatch.setenv("REMOTE_INGEST_URL", "https://mock.ingest.example/ingest")
    monkeypatch.setenv("ETF_PIPELINE_SECRET", "x" * 32)
    monkeypatch.setenv("YAHOOQUERY_MAX_RETRIES", "1")
    monkeypatch.setenv("YAHOOQUERY_BACKOFF_SECONDS", "0")
    monkeypatch.setenv("LOCAL_DB_PATH", str(tmp_path / "e2e.db"))


def _patch_client_with_mock(mock_transport: _MockTransport):
    """Make every httpx.Client inside the pusher route through our mock."""
    from remote_data.pusher import client as push_client

    real_Client = push_client.httpx.Client

    def _factory(*a, **kw):
        # Caller uses Client as context manager, so each `__enter__` returns
        # the same client. We must keep the transport alive for its lifetime.
        return real_Client(transport=mock_transport)

    push_client.httpx.Client = _factory
    return lambda: setattr(push_client.httpx.Client, real_Client)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_e2e_quote_pushed_through_full_pipeline(tmp_path, monkeypatch):
    """9.1 + 9.2: full pipeline from store through mock ingest; verify a quote
    row is in the local DB with pushed_at set, and the mock saw the request."""
    _install_fake_yahooquery()
    _env_setup(monkeypatch, tmp_path)

    mock = _MockTransport()
    from remote_data.pusher import client as push_client
    real_Client = push_client.httpx.Client
    push_client.httpx.Client = lambda *a, **kw: real_Client(transport=mock)

    try:
        from remote_data.config import load_config
        from remote_data.store import local_db
        from remote_data.pusher.loop import run_once

        cfg = load_config()
        db_path = tmp_path / "e2e.db"
        local_db.init(db_path)
        conn = local_db.connect(db_path)

        local_db.insert_etf_quote(conn, [
            {"symbol": "QQQ", "ts": "2026-06-29T13:30:00Z", "price": 521.34, "volume": 1000},
        ])
        summary = run_once(conn, cfg)
        assert summary["pushed"] == 1
        row = conn.execute("SELECT * FROM etf_quote WHERE symbol='QQQ'").fetchone()
        assert row["pushed_at"] is not None

        # Verify mock ingest received the body with correct signature.
        assert len(mock.calls) == 1
        call = mock.calls[0]
        body = call["body"]
        headers = {k.lower(): v for k, v in call["headers"].items()}
        ts = headers["x-etf-pipeline-timestamp"]
        sig = headers["x-etf-pipeline-signature"]
        expected_sig = hmac.new(
            cfg.etf_pipeline_secret.encode(), (ts + "\n").encode() + body,
            hashlib.sha256,
        ).hexdigest()
        assert sig == expected_sig
        parsed = json.loads(body)
        assert parsed["data_type"] == "etf_quote"
        assert len(parsed["records"]) == 1
        assert parsed["records"][0]["symbol"] == "QQQ"
        conn.close()
    finally:
        push_client.httpx.Client = real_Client


def test_e2e_dead_letter_on_4xx(tmp_path, monkeypatch):
    """9.4: 4xx from ingest → etf_dead_letter row + failed_at set on source."""
    _install_fake_yahooquery()
    _env_setup(monkeypatch, tmp_path)

    mock = _MockTransport()
    mock.response_status = 400

    from remote_data.pusher import client as push_client
    real_Client = push_client.httpx.Client
    push_client.httpx.Client = lambda *a, **kw: real_Client(transport=mock)

    try:
        from remote_data.config import load_config
        from remote_data.store import local_db
        from remote_data.pusher.loop import run_once

        cfg = load_config()
        db_path = tmp_path / "e2e_4xx.db"
        local_db.init(db_path)
        conn = local_db.connect(db_path)
        local_db.insert_etf_quote(conn, [
            {"symbol": "SPY", "ts": "2026-06-29T13:30:00Z", "price": 555.0, "volume": 2000},
        ])

        summary = run_once(conn, cfg)
        assert summary["dead_lettered"] == 1
        dl = conn.execute("SELECT * FROM etf_dead_letter").fetchall()
        assert len(dl) == 1
        assert dl[0]["data_type"] == "etf_quote"
        assert dl[0]["response_status"] == 400
        row = conn.execute("SELECT failed_at FROM etf_quote WHERE symbol='SPY'").fetchone()
        assert row["failed_at"] is not None
        conn.close()
    finally:
        push_client.httpx.Client = real_Client


def test_e2e_records_queue_when_server_down(tmp_path, monkeypatch):
    """9.4: network errors → records stay queued (pushed_at=NULL) for retry."""
    _install_fake_yahooquery()
    _env_setup(monkeypatch, tmp_path)

    mock = httpx.MockTransport(lambda _req: (_ for _ in ()).throw(
        httpx.ConnectError("connection refused")
    ))

    from remote_data.pusher import client as push_client
    real_Client = push_client.httpx.Client
    push_client.httpx.Client = lambda *a, **kw: real_Client(transport=mock)

    try:
        from remote_data.store import local_db
        from remote_data.pusher.loop import run_once

        db_path = tmp_path / "e2e_down.db"
        local_db.init(db_path)
        conn = local_db.connect(db_path)
        local_db.insert_etf_quote(conn, [
            {"symbol": "QQQ", "ts": "2026-06-29T13:30:00Z", "price": 1.0, "volume": 1},
        ])

        import time as _time
        real_sleep = _time.sleep
        _time.sleep = lambda *_a, **_k: None
        try:
            summary = run_once(conn)
        finally:
            _time.sleep = real_sleep

        assert summary["retried"] == 1
        row = conn.execute("SELECT pushed_at FROM etf_quote WHERE symbol='QQQ'").fetchone()
        assert row["pushed_at"] is None
        conn.close()
    finally:
        push_client.httpx.Client = real_Client