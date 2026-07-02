"""Read API endpoint tests.

Covers happy paths, 404 on missing data, and pagination.
"""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.etf_read import router as read_router
from backend.services.etf_config import reset_for_test
from backend.services.etf_db import get_conn, init as init_etf_db
from backend.services import etf_service


@pytest.fixture(autouse=True)
def configure(monkeypatch, tmp_path):
    db_path = tmp_path / "etf_remote.db"
    monkeypatch.setenv("ETF_PIPELINE_SECRET", "x" * 32)
    monkeypatch.setenv("REMOTE_DB_PATH", str(db_path))
    init_etf_db()
    reset_for_test()
    yield
    reset_for_test()


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(read_router)
    return app


def _seed_quote(symbol: str, ts: str, price: float) -> None:
    conn = get_conn()
    try:
        etf_service.upsert_quote(
            conn, {"symbol": symbol, "ts": ts, "price": price}
        )
        conn.commit()
    finally:
        conn.close()


def _seed_holdings(symbol: str, items: list) -> None:
    conn = get_conn()
    try:
        etf_service.upsert_holdings(
            conn, {"symbol": symbol, "as_of_date": "2026-06-29", "holdings": items}
        )
        conn.commit()
    finally:
        conn.close()


def _seed_news(symbol: str, items: list) -> None:
    conn = get_conn()
    try:
        for it in items:
            etf_service.insert_news(conn, it)
        conn.commit()
    finally:
        conn.close()


class TestSymbols:
    def test_empty(self):
        client = TestClient(_make_app())
        r = client.get("/api/etf/symbols")
        assert r.status_code == 200
        assert r.json() == {"symbols": []}

    def test_distinct_sorted(self):
        _seed_quote("SPY", "2026-06-29T03:14:00Z", 100.0)
        _seed_quote("QQQ", "2026-06-29T03:14:00Z", 200.0)
        client = TestClient(_make_app())
        r = client.get("/api/etf/symbols")
        assert r.json() == {"symbols": ["QQQ", "SPY"]}


class TestQuote:
    def test_newest_first(self):
        _seed_quote("QQQ", "2026-06-29T03:14:00Z", 100.0)
        _seed_quote("QQQ", "2026-06-29T03:15:00Z", 101.0)
        _seed_quote("QQQ", "2026-06-29T03:16:00Z", 102.0)
        client = TestClient(_make_app())
        r = client.get("/api/etf/quote/QQQ")
        assert r.status_code == 200
        data = r.json()
        assert data["symbol"] == "QQQ"
        assert [q["ts"] for q in data["quotes"]] == [
            "2026-06-29T03:16:00Z",
            "2026-06-29T03:15:00Z",
            "2026-06-29T03:14:00Z",
        ]

    def test_limit(self):
        for i in range(5):
            _seed_quote("QQQ", f"2026-06-29T03:1{i}:00Z", 100.0 + i)
        client = TestClient(_make_app())
        r = client.get("/api/etf/quote/QQQ?limit=2")
        assert len(r.json()["quotes"]) == 2

    def test_missing_returns_404(self):
        client = TestClient(_make_app())
        r = client.get("/api/etf/quote/UNKNOWN")
        assert r.status_code == 404
        assert r.json() == {"detail": "no quote for UNKNOWN"}


class TestFundamentals:
    def test_missing_returns_404(self):
        client = TestClient(_make_app())
        r = client.get("/api/etf/fundamentals/UNKNOWN")
        assert r.status_code == 404
        assert r.json() == {"detail": "no fundamentals for UNKNOWN"}


class TestPayloadEndpoints:
    def test_holdings(self):
        _seed_holdings(
            "QQQ",
            [{"symbol": "AAPL", "name": "Apple", "weight_pct": 5.0}],
        )
        client = TestClient(_make_app())
        r = client.get("/api/etf/holdings/QQQ")
        assert r.status_code == 200
        assert r.json()["holdings"][0]["symbol"] == "AAPL"

    def test_holdings_missing(self):
        client = TestClient(_make_app())
        r = client.get("/api/etf/holdings/UNKNOWN")
        assert r.status_code == 404


class TestNewsPagination:
    def test_pagination(self):
        items = [
            {
                "url": f"https://example.com/n{i}",
                "symbol": "QQQ",
                "title": f"T{i}",
                "publisher": "P",
                "published_at": f"2026-06-29T03:{i:02d}:00Z",
                "summary": "s",
            }
            for i in range(25)
        ]
        _seed_news("QQQ", items)
        client = TestClient(_make_app())
        r = client.get("/api/etf/news/QQQ?page=2&page_size=10")
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 25
        assert data["page"] == 2
        assert data["page_size"] == 10
        assert len(data["news"]) == 10
        # Newest first — page 2 should be items 10..19 by published_at desc
        assert data["news"][0]["title"] == "T14"
        assert data["news"][-1]["title"] == "T5"

    def test_news_missing(self):
        client = TestClient(_make_app())
        r = client.get("/api/etf/news/UNKNOWN")
        assert r.status_code == 404
        assert r.json() == {"detail": "no news for UNKNOWN"}
