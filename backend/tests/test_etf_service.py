"""Persistence service tests.

Covers UPSERT dedupe, INSERT OR IGNORE on news, JSON round-trip, and the
read methods.
"""
from __future__ import annotations

import json

import pytest

from backend.services.etf_db import get_conn, init as init_etf_db
from backend.services import etf_service


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    db_path = tmp_path / "etf_remote.db"
    monkeypatch.setenv("REMOTE_DB_PATH", str(db_path))
    init_etf_db()
    yield


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------


class TestUpsertQuote:
    def test_insert_then_update_same_pk(self):
        conn = get_conn()
        try:
            etf_service.upsert_quote(
                conn, {"symbol": "QQQ", "ts": "2026-06-29T03:14:00Z", "price": 100.0}
            )
            conn.commit()
            etf_service.upsert_quote(
                conn, {"symbol": "QQQ", "ts": "2026-06-29T03:14:00Z", "price": 110.0}
            )
            conn.commit()
        finally:
            conn.close()

        conn = get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM etf_quote WHERE symbol='QQQ'"
            ).fetchall()
        finally:
            conn.close()
        assert len(rows) == 1
        assert rows[0]["price"] == 110.0

    def test_different_ts_does_not_collapse(self):
        conn = get_conn()
        try:
            etf_service.upsert_quote(
                conn, {"symbol": "QQQ", "ts": "2026-06-29T03:14:00Z", "price": 100.0}
            )
            etf_service.upsert_quote(
                conn, {"symbol": "QQQ", "ts": "2026-06-29T03:15:00Z", "price": 101.0}
            )
            conn.commit()
        finally:
            conn.close()

        rows = etf_service.get_latest_quote("QQQ", limit=10)
        assert len(rows) == 2


class TestUpsertFundamentals:
    def test_dedupe(self):
        conn = get_conn()
        try:
            etf_service.upsert_fundamentals(
                conn,
                {"symbol": "QQQ", "as_of": "2026-06-29", "pe": 30.0, "pb": 5.0},
            )
            etf_service.upsert_fundamentals(
                conn,
                {"symbol": "QQQ", "as_of": "2026-06-29", "pe": 32.4, "pb": 5.5},
            )
            conn.commit()
        finally:
            conn.close()

        row = etf_service.get_fundamentals("QQQ")
        assert row["pe"] == 32.4
        assert row["pb"] == 5.5


class TestUpsertHoldings:
    def test_json_round_trip(self):
        holdings = [
            {"symbol": "AAPL", "name": "Apple", "weight_pct": 5.0},
            {"symbol": "MSFT", "name": "Microsoft", "weight_pct": 4.5},
        ]
        conn = get_conn()
        try:
            etf_service.upsert_holdings(
                conn,
                {
                    "symbol": "QQQ",
                    "as_of_date": "2026-06-29",
                    "holdings": holdings,
                },
            )
            conn.commit()
        finally:
            conn.close()

        out = etf_service.get_holdings("QQQ")
        assert out["as_of_date"] == "2026-06-29"
        assert out["holdings"] == holdings

    def test_dedupe_overwrites_payload(self):
        conn = get_conn()
        try:
            etf_service.upsert_holdings(
                conn,
                {
                    "symbol": "QQQ",
                    "as_of_date": "2026-06-29",
                    "holdings": [{"symbol": "AAPL", "weight_pct": 5.0}],
                },
            )
            etf_service.upsert_holdings(
                conn,
                {
                    "symbol": "QQQ",
                    "as_of_date": "2026-06-29",
                    "holdings": [{"symbol": "MSFT", "weight_pct": 4.0}],
                },
            )
            conn.commit()
        finally:
            conn.close()

        out = etf_service.get_holdings("QQQ")
        assert len(out["holdings"]) == 1
        assert out["holdings"][0]["symbol"] == "MSFT"


class TestUpsertPerformance:
    def test_wire_to_sql_field_mapping(self):
        """The wire format uses ytd_return/return_1y/...; SQL uses ytd/1y/...."""
        conn = get_conn()
        try:
            etf_service.upsert_performance(
                conn,
                {
                    "symbol": "QQQ",
                    "as_of_date": "2026-06-29",
                    "ytd_return": 0.12,
                    "return_1y": 0.25,
                    "return_3y": 0.40,
                    "return_5y": 0.95,
                    "return_10y": 4.10,
                },
            )
            conn.commit()
        finally:
            conn.close()

        out = etf_service.get_performance("QQQ")
        assert out["ytd"] == 0.12
        assert out["1y"] == 0.25
        assert out["3y"] == 0.40
        assert out["5y"] == 0.95
        assert out["10y"] == 4.10


class TestInsertNews:
    def test_insert_or_ignore(self):
        rec = {
            "url": "https://example.com/x",
            "symbol": "QQQ",
            "title": "T",
            "publisher": "P",
            "published_at": "2026-06-29T03:14:00Z",
            "summary": "S",
        }
        conn = get_conn()
        try:
            assert etf_service.insert_news(conn, rec) is True
            conn.commit()
        finally:
            conn.close()

        # Second insert with different title but same url — silently ignored.
        rec["title"] = "T-updated"
        conn = get_conn()
        try:
            assert etf_service.insert_news(conn, rec) is False
            conn.commit()
        finally:
            conn.close()

        out = etf_service.get_news("QQQ", page=1, page_size=10)
        assert out["total"] == 1
        assert out["items"][0]["title"] == "T"  # original preserved


class TestListSymbols:
    def test_distinct_sorted(self):
        conn = get_conn()
        try:
            etf_service.upsert_quote(conn, {"symbol": "SPY", "ts": "2026-06-29T03:14:00Z"})
            etf_service.upsert_quote(conn, {"symbol": "QQQ", "ts": "2026-06-29T03:14:00Z"})
            etf_service.upsert_fundamentals(
                conn, {"symbol": "QQQ", "as_of": "2026-06-29"}
            )
            etf_service.insert_news(
                conn,
                {
                    "url": "https://example.com/agg",
                    "symbol": "AGG",
                    "title": "t",
                    "publisher": "p",
                    "published_at": "2026-06-29T03:14:00Z",
                    "summary": "s",
                },
            )
            conn.commit()
        finally:
            conn.close()

        syms = etf_service.list_symbols()
        assert syms == ["AGG", "QQQ", "SPY"]


class TestHealthSnapshot:
    def test_no_ingest_yet(self):
        snap = etf_service.health_snapshot()
        assert snap["last_ingest_at"] is None
        assert snap["last_batch_id"] is None
        assert snap["symbols_covered"] == 0

    def test_counts_distinct_symbols(self):
        conn = get_conn()
        try:
            etf_service.upsert_quote(conn, {"symbol": "SPY", "ts": "x"})
            etf_service.upsert_quote(conn, {"symbol": "QQQ", "ts": "x"})
            etf_service.upsert_quote(conn, {"symbol": "QQQ", "ts": "y"})
            conn.execute(
                "INSERT INTO etf_ingest_log(batch_id, data_type, source_ip, accepted, rejected, received_at) "
                "VALUES(?, ?, ?, ?, ?, ?)",
                ("b1", "etf_quote", "1.2.3.4", 2, 0, "2026-06-29T03:14:00Z"),
            )
            conn.commit()
        finally:
            conn.close()

        snap = etf_service.health_snapshot()
        assert snap["last_ingest_at"] == "2026-06-29T03:14:00Z"
        assert snap["last_batch_id"] == "b1"
        assert snap["symbols_covered"] == 2
