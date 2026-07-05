"""Tests for the ETF-aware valuation wrapper.

Covers the dynamic symbol-set cache (case-insensitive membership, lazy load,
explicit refresh), the merge of `etf_fundamentals` into the Futu response for
ETFs, and the uniform error/non-ETF shapes.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.services.etf_db import get_conn, init as init_etf_db
from backend.services import etf_service, etf_valuation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Per-test etf_remote.db + reset the in-memory ETF symbol cache."""
    db_path = tmp_path / "etf_remote.db"
    monkeypatch.setenv("REMOTE_DB_PATH", str(db_path))
    init_etf_db()
    # Always start with an empty cache so cache-miss-vs-hit tests are deterministic.
    etf_valuation._ETF_SYMBOLS = None
    yield
    etf_valuation._ETF_SYMBOLS = None


def _seed_fundamentals(symbol: str, **fields) -> None:
    """Insert one `etf_fundamentals` row for `symbol` with the given fields."""
    record = {"symbol": symbol, "as_of": "2026-07-02T03:17:28Z", **fields}
    conn = get_conn()
    try:
        etf_service.upsert_fundamentals(conn, record)
        conn.commit()
    finally:
        conn.close()


def _futu_response(symbol: str = "QQQ") -> dict:
    """A realistic FutuQuoteService.get_daily_basic response."""
    return {
        "symbol": symbol,
        "data": [
            {
                "trade_date": "2026-07-01",
                "pe_ttm": 25.0,
                "pb": 4.0,
                "turnover_rate": 0.015,
                "total_mv": 250_000_000_000,
                "circ_mv": 240_000_000_000,
            },
            {
                "trade_date": "2026-07-02",
                "pe_ttm": 25.5,
                "pb": 4.1,
                "turnover_rate": 0.017,
                "total_mv": 252_000_000_000,
                "circ_mv": 242_000_000_000,
            },
        ],
        "latest": {
            "trade_date": "2026-07-02",
            "pe_ttm": 25.5,
            "pb": 4.1,
            "turnover_rate": 0.017,
            "total_mv": 252_000_000_000,
            "circ_mv": 242_000_000_000,
        },
    }


# ---------------------------------------------------------------------------
# Cache behavior
# ---------------------------------------------------------------------------


class TestIsEtfCache:
    def test_cache_miss_populates_from_db(self):
        _seed_fundamentals("QQQ", pe=33.0)
        _seed_fundamentals("SPY", pe=22.0)

        with patch.object(
            etf_valuation.etf_service, "get_conn", wraps=get_conn
        ) as wrapped_conn:
            assert etf_valuation.is_etf("QQQ") is True

        assert etf_valuation._ETF_SYMBOLS == {"QQQ", "SPY"}

    def test_cache_hit_skips_db(self):
        _seed_fundamentals("QQQ", pe=33.0)
        # First call populates.
        etf_valuation.is_etf("QQQ")

        # Second call must not open a connection. We patch get_conn to a
        # function that raises if invoked — proving the cache short-circuits.
        def must_not_open(*args, **kwargs):
            raise AssertionError("get_conn should not be called on cache hit")

        with patch.object(etf_valuation.etf_service, "get_conn", side_effect=must_not_open):
            assert etf_valuation.is_etf("QQQ") is True
            assert etf_valuation.is_etf("qqq") is True  # case-insensitive too

    def test_is_etf_is_case_insensitive(self):
        _seed_fundamentals("QQQ", pe=33.0)
        assert etf_valuation.is_etf("qqq") is True
        assert etf_valuation.is_etf("QqQ") is True
        assert etf_valuation.is_etf("QQQ") is True

    def test_non_etf_returns_false(self):
        _seed_fundamentals("QQQ", pe=33.0)
        assert etf_valuation.is_etf("AAPL") is False
        assert etf_valuation.is_etf("MSFT") is False


# ---------------------------------------------------------------------------
# Merge behavior — get_etf_aware_daily_basic
# ---------------------------------------------------------------------------


class TestGetEtfAwareDailyBasic:
    def test_etf_with_row_overrides_pe_pb_and_adds_dividend_fields(self):
        _seed_fundamentals(
            "QQQ",
            pe=33.295002,
            pb=None,
            dividend_yield=0.002403585,
            dividend_rate=1.77,
        )

        with patch.object(
            etf_valuation.FutuQuoteService,
            "get_daily_basic",
            return_value=_futu_response("QQQ"),
        ):
            out = etf_valuation.get_etf_aware_daily_basic("QQQ", 30)

        assert out["is_etf"] is True
        latest = out["latest"]
        assert latest["pe_ttm"] == 33.295002  # overridden from yahooquery
        assert latest["pb"] is None           # yahooquery null wins over Futu 4.1
        assert latest["dividend_yield"] == 0.002403585
        assert latest["dividend_rate"] == 1.77
        assert latest["as_of"] == "2026-07-02T03:17:28Z"
        # Futu-sourced fields preserved.
        assert latest["total_mv"] == 252_000_000_000
        assert latest["turnover_rate"] == 0.017
        # Historical series is the Futu K-line (unchanged).
        assert len(out["data"]) == 2
        assert out["data"][0]["pe_ttm"] == 25.0  # older bar still Futu-sourced

    def test_non_etf_returns_futu_with_is_etf_false(self):
        _seed_fundamentals("QQQ", pe=33.0)  # QQQ is in the set
        futu = _futu_response("AAPL")

        with patch.object(
            etf_valuation.FutuQuoteService,
            "get_daily_basic",
            return_value=futu,
        ):
            out = etf_valuation.get_etf_aware_daily_basic("AAPL", 30)

        assert out["is_etf"] is False
        # Every Futu field preserved byte-for-byte.
        assert out["symbol"] == "AAPL"
        assert out["latest"]["pe_ttm"] == 25.5
        assert out["latest"]["pb"] == 4.1
        assert out["latest"]["total_mv"] == 252_000_000_000
        # Dividend / as_of nulls added so the shape is uniform across branches.
        assert out["latest"]["dividend_yield"] is None
        assert out["latest"]["dividend_rate"] is None
        assert out["latest"]["as_of"] is None

    def test_etf_symbol_with_no_row_keeps_futu_pe_and_nulls_dividends(self):
        # NEWETF is in the cached set (seeded below) but get_fundamentals
        # returns None — simulating either a freshly-deleted row or a stale
        # cache that hasn't been refreshed yet.
        _seed_fundamentals("NEWETF", pe=33.0)
        futu = _futu_response("NEWETF")

        with patch.object(
            etf_valuation.FutuQuoteService,
            "get_daily_basic",
            return_value=futu,
        ), patch.object(
            etf_valuation.etf_service, "get_fundamentals", return_value=None
        ):
            out = etf_valuation.get_etf_aware_daily_basic("NEWETF", 30)

        assert out["is_etf"] is True
        # Futu PE preserved (no override applied).
        assert out["latest"]["pe_ttm"] == 25.5
        assert out["latest"]["pb"] == 4.1
        assert out["latest"]["dividend_yield"] is None
        assert out["latest"]["dividend_rate"] is None
        assert out["latest"]["as_of"] is None

    def test_futu_error_path_returns_error_dict_with_is_etf_false(self):
        err = {"symbol": "QQQ", "error": "Futu connection refused"}

        with patch.object(
            etf_valuation.FutuQuoteService,
            "get_daily_basic",
            return_value=err,
        ):
            out = etf_valuation.get_etf_aware_daily_basic("QQQ", 30)

        assert out["error"] == "Futu connection refused"
        assert out["is_etf"] is False
        # No exception escapes — and we do NOT touch the ETF cache / DB on error.

    def test_pb_override_with_non_null_yahooquery_value(self):
        """If yahooquery returned a real pb, it wins over Futu's snapshot."""
        _seed_fundamentals("QQQ", pe=33.0, pb=5.5, dividend_yield=0.01, dividend_rate=2.0)

        with patch.object(
            etf_valuation.FutuQuoteService,
            "get_daily_basic",
            return_value=_futu_response("QQQ"),
        ):
            out = etf_valuation.get_etf_aware_daily_basic("QQQ", 30)

        assert out["latest"]["pb"] == 5.5  # yahooquery wins over Futu 4.1


# ---------------------------------------------------------------------------
# refresh_etf_symbols
# ---------------------------------------------------------------------------


class TestRefreshEtfSymbols:
    def test_refresh_clears_and_repopulates_cache(self):
        _seed_fundamentals("QQQ", pe=33.0)

        # Prime the cache.
        assert etf_valuation.is_etf("QQQ") is True
        assert etf_valuation._ETF_SYMBOLS == {"QQQ"}

        # Add a new symbol directly to the DB and refresh.
        _seed_fundamentals("SCHD", pe=20.0)
        loaded = etf_valuation.refresh_etf_symbols()

        assert loaded == {"QQQ", "SCHD"}
        assert etf_valuation._ETF_SYMBOLS == {"QQQ", "SCHD"}
        assert etf_valuation.is_etf("SCHD") is True

    def test_refresh_on_empty_db_returns_empty_set(self):
        loaded = etf_valuation.refresh_etf_symbols()
        assert loaded == set()
        assert etf_valuation._ETF_SYMBOLS == set()
        assert etf_valuation.is_etf("QQQ") is False