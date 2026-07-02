"""Ingest endpoint tests.

Covers each data_type happy path, partial success, top-level schema failure,
oversized body, and unknown data_type. Tests bypass the HMAC / rate-limit
middleware by mounting the router directly (those have their own test files).
"""
from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.etf_ingest import router as ingest_router
from backend.services.etf_config import reset_for_test
from backend.services.etf_db import get_conn, init as init_etf_db


SECRET = "x" * 32


@pytest.fixture(autouse=True)
def configure(monkeypatch, tmp_path):
    db_path = tmp_path / "etf_remote.db"
    monkeypatch.setenv("ETF_PIPELINE_SECRET", SECRET)
    monkeypatch.setenv("REMOTE_DB_PATH", str(db_path))
    monkeypatch.setenv("INGEST_MAX_BODY_BYTES", "1048576")
    init_etf_db()
    reset_for_test()
    yield
    reset_for_test()


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(ingest_router)
    return app


def _sign(timestamp: str, body: bytes) -> dict:
    """Sign the body so the HMAC middleware (when stacked) accepts it.

    Tests below don't add the HMAC middleware — they mount the router
    directly — but the helper is here in case a future test wants to stack.
    """
    msg = timestamp.encode("utf-8") + b"\n" + body
    sig = hmac.new(SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return {
        "X-ETF-Pipeline-Timestamp": timestamp,
        "X-ETF-Pipeline-Signature": sig,
    }


def _row_count(table: str) -> int:
    conn = get_conn()
    try:
        return conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
    finally:
        conn.close()


class TestHappyPaths:
    def test_etf_quote(self):
        client = TestClient(_make_app())
        body = {
            "data_type": "etf_quote",
            "batch_id": "b1",
            "records": [
                {"symbol": "QQQ", "ts": "2026-06-29T03:14:00Z", "price": 100.0},
                {"symbol": "SPY", "ts": "2026-06-29T03:14:00Z", "price": 200.0},
            ],
        }
        r = client.post("/api/etf/ingest", json=body)
        assert r.status_code == 200
        assert r.json() == {"accepted": 2, "rejected": 0, "batch_id": "b1"}
        assert _row_count("etf_quote") == 2

    def test_etf_fundamentals(self):
        client = TestClient(_make_app())
        body = {
            "data_type": "etf_fundamentals",
            "batch_id": "b2",
            "records": [{"symbol": "QQQ", "as_of": "2026-06-29", "pe": 32.4}],
        }
        r = client.post("/api/etf/ingest", json=body)
        assert r.status_code == 200
        assert r.json()["accepted"] == 1
        assert _row_count("etf_fundamentals") == 1

    def test_etf_holdings(self):
        client = TestClient(_make_app())
        body = {
            "data_type": "etf_holdings",
            "batch_id": "b3",
            "records": [
                {
                    "symbol": "QQQ",
                    "as_of_date": "2026-06-29",
                    "holdings": [{"symbol": "AAPL", "name": "Apple", "weight_pct": 5.0}],
                }
            ],
        }
        r = client.post("/api/etf/ingest", json=body)
        assert r.status_code == 200
        assert r.json()["accepted"] == 1
        assert _row_count("etf_holdings") == 1

    def test_etf_news(self):
        client = TestClient(_make_app())
        body = {
            "data_type": "etf_news",
            "batch_id": "b4",
            "records": [
                {
                    "url": "https://example.com/x",
                    "symbol": "QQQ",
                    "title": "T",
                    "publisher": "P",
                    "published_at": "2026-06-29T03:14:00Z",
                    "summary": "S",
                }
            ],
        }
        r = client.post("/api/etf/ingest", json=body)
        assert r.status_code == 200
        assert r.json()["accepted"] == 1
        assert _row_count("etf_news") == 1


class TestPartialSuccess:
    def test_one_record_invalid_returns_207(self):
        client = TestClient(_make_app())
        body = {
            "data_type": "etf_quote",
            "batch_id": "b5",
            "records": [
                {"symbol": "QQQ", "ts": "2026-06-29T03:14:00Z", "price": 100.0},
                {"symbol": "SPY", "ts": "2026-06-29T03:14:00Z", "price": 200.0},
                # Missing `ts` — invalid record.
                {"symbol": "AGG", "price": 50.0},
                {"symbol": "VTI", "ts": "2026-06-29T03:14:00Z", "price": 80.0},
                {"symbol": "IWM", "ts": "2026-06-29T03:14:00Z", "price": 70.0},
            ],
        }
        r = client.post("/api/etf/ingest", json=body)
        assert r.status_code == 207
        body = r.json()
        assert body["accepted"] == 4
        assert body["rejected"] == 1
        assert body["batch_id"] == "b5"
        assert len(body["errors"]) == 1
        assert body["errors"][0]["index"] == 2
        assert "ts" in body["errors"][0]["error"]
        # 4 rows landed in etf_quote
        assert _row_count("etf_quote") == 4

    def test_all_records_invalid_returns_400(self):
        client = TestClient(_make_app())
        body = {
            "data_type": "etf_quote",
            "batch_id": "b6",
            "records": [
                {"price": 100.0},  # missing symbol + ts
                {"price": 200.0},  # missing symbol + ts
            ],
        }
        r = client.post("/api/etf/ingest", json=body)
        assert r.status_code == 400
        assert _row_count("etf_quote") == 0


class TestTopLevelFailures:
    def test_unknown_data_type_returns_400(self):
        client = TestClient(_make_app())
        body = {"data_type": "etf_kline", "batch_id": "b", "records": []}
        r = client.post("/api/etf/ingest", json=body)
        assert r.status_code == 400

    def test_missing_batch_id_returns_400(self):
        client = TestClient(_make_app())
        body = {"data_type": "etf_quote", "records": []}
        r = client.post("/api/etf/ingest", json=body)
        assert r.status_code == 400


class TestBodySize:
    def test_oversized_body_returns_413(self, monkeypatch):
        # Set the cap to a tiny value to avoid generating a 1MB+ payload.
        monkeypatch.setenv("INGEST_MAX_BODY_BYTES", "100")
        reset_for_test()
        client = TestClient(_make_app())
        body = {
            "data_type": "etf_quote",
            "batch_id": "b",
            "records": [{"symbol": "QQQ", "ts": "x" * 200, "price": 1.0}],
        }
        r = client.post("/api/etf/ingest", json=body)
        assert r.status_code == 413
        assert _row_count("etf_ingest_log") == 1


class TestIngestLog:
    def test_audit_row_written_for_successful_ingest(self):
        client = TestClient(_make_app())
        body = {
            "data_type": "etf_quote",
            "batch_id": "audit-1",
            "records": [{"symbol": "QQQ", "ts": "2026-06-29T03:14:00Z", "price": 100.0}],
        }
        client.post("/api/etf/ingest", json=body)
        conn = get_conn()
        try:
            rows = conn.execute("SELECT * FROM etf_ingest_log").fetchall()
        finally:
            conn.close()
        assert len(rows) == 1
        assert rows[0]["batch_id"] == "audit-1"
        assert rows[0]["data_type"] == "etf_quote"
        assert rows[0]["accepted"] == 1
        assert rows[0]["rejected"] == 0
