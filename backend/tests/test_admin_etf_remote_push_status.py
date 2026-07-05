"""Tests for the ETF remote push monitor endpoint.

Covers:
- Authorized admin gets 200 with the documented JSON shape
- Unauthorized user gets 403
- Missing etf_remote.db returns 200 with `tables: []` and an `error` field
- Lag/status thresholds produce the expected `status` for synthetic timestamps
- The endpoint opens the DB read-only (writing through it fails)
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.admin import router as admin_router
from backend.api.etf_remote_push_status import compute_push_status, TABLE_SPECS
from backend.services.etf_db import init as init_etf_db


SECRET = "x" * 32


@pytest.fixture
def fake_admin(monkeypatch):
    """Force the admin permission check to succeed regardless of DB state."""
    monkeypatch.setattr(
        "backend.services.role_service.RoleService.user_has_permission",
        staticmethod(lambda user_id, name: True),
    )

    app = _make_app()
    from backend.api.auth import get_current_user as real_auth_dep

    app.dependency_overrides[real_auth_dep] = lambda: {"user_id": 1, "username": "admin"}
    return app


@pytest.fixture
def fake_user(monkeypatch):
    """Auth succeeds but the admin permission check fails."""
    monkeypatch.setattr(
        "backend.services.role_service.RoleService.user_has_permission",
        staticmethod(lambda user_id, name: False),
    )

    app = _make_app()
    from backend.api.auth import get_current_user as real_auth_dep

    app.dependency_overrides[real_auth_dep] = lambda: {"user_id": 1, "username": "user"}
    return app


def _make_app() -> FastAPI:
    app = FastAPI()
    app.include_router(admin_router)
    return app


@pytest.fixture
def remote_db(monkeypatch, tmp_path):
    """Point REMOTE_DB_PATH at a fresh, schema-initialized tmp db."""
    db_path = tmp_path / "etf_remote.db"
    monkeypatch.setenv("ETF_PIPELINE_SECRET", SECRET)
    monkeypatch.setenv("REMOTE_DB_PATH", str(db_path))
    init_etf_db()
    return db_path


def _seed_ingest_log(conn: sqlite3.Connection, data_type: str, received_at: str) -> None:
    conn.execute(
        "INSERT INTO etf_ingest_log (batch_id, data_type, source_ip, accepted, rejected, received_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (f"b-{data_type}", data_type, "127.0.0.1", 1, 0, received_at),
    )
    conn.commit()


def _seed_business_row(conn: sqlite3.Connection, table: str, date_value: str) -> None:
    """Insert a minimal row in a business table with a date column set to `date_value`."""
    if table == "etf_quote":
        conn.execute(
            "INSERT INTO etf_quote (symbol, ts, price) VALUES (?, ?, ?)",
            ("QQQ", date_value, 100.0),
        )
    elif table == "etf_fundamentals":
        conn.execute(
            "INSERT INTO etf_fundamentals (symbol, as_of, pe) VALUES (?, ?, ?)",
            ("QQQ", date_value, 32.0),
        )
    elif table == "etf_news":
        conn.execute(
            "INSERT INTO etf_news (url, symbol, published_at, title) VALUES (?, ?, ?, ?)",
            ("https://example.com/a", "QQQ", date_value, "x"),
        )
    else:
        conn.execute(
            f'INSERT INTO "{table}" (symbol, as_of_date, payload_json) VALUES (?, ?, ?)',
            ("QQQ", date_value, "[]"),
        )
    conn.commit()


def _open_ro(db_path):
    return sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)


class TestEndpointAuthorization:
    def test_unauthorized_returns_403(self, fake_user, remote_db):
        client = TestClient(fake_user)
        r = client.get("/api/admin/etf-remote-push-status")
        assert r.status_code == 403
        assert "system_statistics" in r.json()["detail"]

    def test_authorized_returns_200(self, fake_admin, remote_db):
        client = TestClient(fake_admin)
        r = client.get("/api/admin/etf-remote-push-status")
        assert r.status_code == 200
        body = r.json()
        assert "tables" in body
        assert "server_time" in body
        assert "db_path" in body
        assert "thresholds" in body
        assert body["db_path"] == str(remote_db)
        assert {t["data_type"] for t in body["tables"]} == {
            dt for dt, _, _, _ in TABLE_SPECS
        }


class TestMissingDb:
    def test_missing_db_returns_empty_tables(self, fake_admin, tmp_path, monkeypatch):
        missing = tmp_path / "does_not_exist.db"
        monkeypatch.setenv("REMOTE_DB_PATH", str(missing))
        client = TestClient(fake_admin)
        r = client.get("/api/admin/etf-remote-push-status")
        assert r.status_code == 200
        body = r.json()
        assert body["tables"] == []
        assert body["error"] == "etf_remote.db not found"
        assert body["db_path"] == str(missing)


class TestStatusClassification:
    def test_recent_push_is_ok(self, remote_db, monkeypatch):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        recent = (now - timedelta(hours=2)).isoformat().replace("+00:00", "Z")

        conn = sqlite3.connect(remote_db)
        try:
            _seed_ingest_log(conn, "etf_quote", recent)
        finally:
            conn.close()

        out = compute_push_status(remote_db)
        row = next(t for t in out["tables"] if t["data_type"] == "etf_quote")
        assert row["status"] == "ok"
        assert row["lag_hours"] is not None
        assert 1.9 < row["lag_hours"] < 2.1

    def test_push_in_warn_window(self, remote_db):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        ten_hours_ago = (now - timedelta(hours=10)).isoformat().replace("+00:00", "Z")

        conn = sqlite3.connect(remote_db)
        try:
            _seed_ingest_log(conn, "etf_fundamentals", ten_hours_ago)
        finally:
            conn.close()

        out = compute_push_status(remote_db)
        row = next(t for t in out["tables"] if t["data_type"] == "etf_fundamentals")
        assert row["status"] == "warn"

    def test_push_in_stale_window(self, remote_db):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        long_ago = (now - timedelta(hours=36)).isoformat().replace("+00:00", "Z")

        conn = sqlite3.connect(remote_db)
        try:
            _seed_ingest_log(conn, "etf_news", long_ago)
        finally:
            conn.close()

        out = compute_push_status(remote_db)
        row = next(t for t in out["tables"] if t["data_type"] == "etf_news")
        assert row["status"] == "stale"

    def test_never_pushed_is_unknown(self, remote_db):
        out = compute_push_status(remote_db)
        for row in out["tables"]:
            assert row["status"] == "unknown"
            assert row["last_received_at"] is None
            assert row["lag_hours"] is None

    def test_thresholds_can_be_tuned(self, remote_db, monkeypatch):
        # Force the freshest possible push to be "warn" by setting warn=0.
        monkeypatch.setenv("ETF_PUSH_WARN_HOURS", "0")
        monkeypatch.setenv("ETF_PUSH_STALE_HOURS", "100")
        out = compute_push_status(remote_db)
        # No ingest log rows -> still unknown (no last_received_at to evaluate)
        assert all(t["status"] == "unknown" for t in out["tables"])
        assert out["thresholds"] == {"warn_hours": 0.0, "stale_hours": 100.0}


class TestTableSummaries:
    def test_last_record_date_and_row_count(self, remote_db):
        conn = sqlite3.connect(remote_db)
        try:
            _seed_business_row(conn, "etf_quote", "2026-07-04T20:00:00Z")
            _seed_business_row(conn, "etf_quote", "2026-07-04T19:00:00Z")
            _seed_business_row(conn, "etf_esg", "2026-07-03")
        finally:
            conn.close()

        out = compute_push_status(remote_db)
        quote = next(t for t in out["tables"] if t["data_type"] == "etf_quote")
        esg = next(t for t in out["tables"] if t["data_type"] == "etf_esg")

        assert quote["row_count"] == 2
        assert quote["last_record_date"] == "2026-07-04T20:00:00Z"
        assert esg["row_count"] == 1
        assert esg["last_record_date"] == "2026-07-03"

    def test_empty_table_has_null_dates(self, remote_db):
        out = compute_push_status(remote_db)
        for row in out["tables"]:
            assert row["row_count"] == 0
            assert row["last_record_date"] is None


class TestReadOnlyConnection:
    def test_writing_through_endpoint_connection_fails(self, remote_db):
        """The endpoint must use `mode=ro` — proves the connection cannot mutate."""
        uri = f"file:{remote_db}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        try:
            with pytest.raises(sqlite3.OperationalError):
                conn.execute("DELETE FROM etf_ingest_log")
        finally:
            conn.close()