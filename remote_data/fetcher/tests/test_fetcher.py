"""Unit tests for fetcher modules — all yahooquery calls mocked.

These tests verify that each fetcher returns the normalized record shape
documented in `etf-fetcher/spec.md` regardless of upstream quirks.
"""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Fake yahooquery.Ticker that returns canned responses.
# ---------------------------------------------------------------------------


class _FakeTicker:
    def __init__(self, symbol, **kwargs):
        self.symbol = symbol
        self._price = {
            "regularMarketTime": 1751200000,
            "regularMarketPrice": 521.34,
            "preMarketPrice": 522.10,
            "postMarketPrice": None,
            "regularMarketVolume": 1234567,
        }

    @property
    def price(self):
        return {self.symbol: self._price}

    @property
    def summary_detail(self):
        return {
            self.symbol: {
                "trailingPE": 28.5,
                "priceToBook": 7.2,
                "dividendYield": 0.0055,
                "dividendRate": 2.87,
            }
        }

    @property
    def key_stats(self):
        return {self.symbol: {}}

    @property
    def fund_holding_info(self):
        return {
            self.symbol: {
                "asOfDate": "2026-06-15",
                "holdings": {
                    "AAPL": {"name": "Apple Inc.", "weight": 0.082},
                    "MSFT": {"name": "Microsoft", "weight": 0.077},
                },
            }
        }

    @property
    def fund_sector_weightings(self):
        return {
            self.symbol: {
                "asOfDate": "2026-06-15",
                "Technology": 0.45,
                "Healthcare": 0.13,
            }
        }

    @property
    def fund_performance(self):
        return {
            self.symbol: {
                "asOfDate": "2026-06-15",
                "performanceOverview": {
                    "ytdReturn": 0.123,
                    "oneYearReturn": 0.234,
                    "threeYearReturn": 0.456,
                    "fiveYearReturn": 0.789,
                    "tenYearReturn": 1.234,
                },
            }
        }

    @property
    def fund_esg_scores(self):
        return {
            self.symbol: {
                "asOfDate": "2026-06-01",
                "totalEsg": 22.5,
                "environmentScore": 7.1,
                "socialScore": 8.3,
                "governanceScore": 7.1,
            }
        }

    @property
    def news(self):
        return [
            {
                "title": "QQQ climbs",
                "publisher": "Reuters",
                "link": "https://example.com/qqq-1",
                "providerPublishTime": 1751200000,
                "summary": "summary text",
            }
        ]


class _FakeYahooQueryModule(types.ModuleType):
    Ticker = _FakeTicker


@pytest.fixture()
def fake_yq(monkeypatch):
    sys.modules["yahooquery"] = _FakeYahooQueryModule("yahooquery")
    yield
    sys.modules.pop("yahooquery", None)


# Each test patches config (env vars) and the fake Ticker at the same time.

def _patch_config(monkeypatch, **values):
    defaults = {
        "DEPLOY_ROLE": "LOCAL",
        "REMOTE_INGEST_URL": "https://example.com/ingest",
        "ETF_PIPELINE_SECRET": "x" * 32,
        "YAHOOQUERY_MAX_RETRIES": "1",
        "YAHOOQUERY_BACKOFF_SECONDS": "0",
    }
    defaults.update(values)
    for k, v in defaults.items():
        monkeypatch.setenv(k, v)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_fetch_quotes_shape(monkeypatch, fake_yq):
    _patch_config(monkeypatch)
    from remote_data.fetcher.etf_quote import fetch_quotes

    out = fetch_quotes(["QQQ"])
    assert len(out) == 1
    rec = out[0]
    assert rec["symbol"] == "QQQ"
    assert rec["price"] == 521.34
    assert rec["pre_market_price"] == 522.10
    assert rec["post_market_price"] is None
    assert rec["volume"] == 1234567
    assert rec["ts"].endswith("Z")


def test_fetch_fundamentals_shape(monkeypatch, fake_yq):
    _patch_config(monkeypatch)
    from remote_data.fetcher.etf_fundamentals import fetch_fundamentals

    out = fetch_fundamentals(["QQQ"])
    assert len(out) == 1
    rec = out[0]
    assert rec["symbol"] == "QQQ"
    assert rec["as_of"].endswith("Z")
    assert rec["pe"] == 28.5
    assert rec["pb"] == 7.2
    assert rec["dividend_yield"] == 0.0055
    assert rec["dividend_rate"] == 2.87


def test_fetch_holdings_shape(monkeypatch, fake_yq):
    _patch_config(monkeypatch)
    from remote_data.fetcher.etf_holdings import fetch_holdings

    out = fetch_holdings(["QQQ"])
    assert len(out) == 1
    rec = out[0]
    assert rec["symbol"] == "QQQ"
    assert rec["as_of_date"] == "2026-06-15"
    assert isinstance(rec["holdings"], list)
    assert rec["holdings"][0]["symbol"] == "AAPL"
    assert rec["holdings"][0]["weight_pct"] == 0.082


def test_fetch_sector_weightings_shape(monkeypatch, fake_yq):
    _patch_config(monkeypatch)
    from remote_data.fetcher.etf_sector_weightings import fetch_sector_weightings

    out = fetch_sector_weightings(["QQQ"])
    assert len(out) == 1
    rec = out[0]
    assert rec["as_of_date"] == "2026-06-15"
    sectors = {s["sector"]: s["weight_pct"] for s in rec["sectors"]}
    assert sectors["Technology"] == 0.45


def test_fetch_performance_shape(monkeypatch, fake_yq):
    _patch_config(monkeypatch)
    from remote_data.fetcher.etf_performance import fetch_performance

    out = fetch_performance(["QQQ"])
    assert len(out) == 1
    rec = out[0]
    assert rec["ytd_return"] == 0.123
    assert rec["return_1y"] == 0.234
    assert rec["return_3y"] == 0.456
    assert rec["return_5y"] == 0.789
    assert rec["return_10y"] == 1.234


def test_fetch_equity_holdings_shape(monkeypatch, fake_yq):
    _patch_config(monkeypatch)
    from remote_data.fetcher.etf_equity_holdings import fetch_equity_holdings

    out = fetch_equity_holdings(["QQQ"])
    assert len(out) == 1
    rec = out[0]
    assert rec["symbol"] == "QQQ"
    assert isinstance(rec["holdings"], list)


def test_fetch_esg_shape(monkeypatch, fake_yq):
    _patch_config(monkeypatch)
    from remote_data.fetcher.etf_esg import fetch_esg

    out = fetch_esg(["QQQ"])
    assert len(out) == 1
    rec = out[0]
    assert rec["total_esg"] == 22.5
    assert rec["environment"] == 7.1
    assert rec["social"] == 8.3
    assert rec["governance"] == 7.1


def test_fetch_news_shape(monkeypatch, fake_yq):
    _patch_config(monkeypatch)
    from remote_data.fetcher.etf_news import fetch_news

    out = fetch_news(["QQQ"])
    assert len(out) == 1
    rec = out[0]
    assert rec["url"] == "https://example.com/qqq-1"
    assert rec["publisher"] == "Reuters"
    assert rec["published_at"].endswith("Z")


def test_one_symbol_failure_does_not_raise(monkeypatch, fake_yq):
    _patch_config(monkeypatch)

    # Make Ticker raise for a specific symbol; OK for the other.
    real_ticker = _FakeTicker

    class SelectiveTicker(real_ticker):
        def __init__(self, symbol, **kwargs):
            if symbol == "BAD":
                raise RuntimeError("yahooquery blew up")
            super().__init__(symbol, **kwargs)

    sys.modules["yahooquery"].Ticker = SelectiveTicker

    from remote_data.fetcher.etf_quote import fetch_quotes

    out = fetch_quotes(["QQQ", "BAD"])
    assert len(out) == 1
    assert out[0]["symbol"] == "QQQ"


def test_epoch_to_iso_handles_bad_input():
    from remote_data.fetcher.base import epoch_to_iso
    assert epoch_to_iso(None) is None
    assert epoch_to_iso("not-a-number") is None
    assert epoch_to_iso(0) is not None


def test_retry_policy_delays():
    from remote_data.fetcher.base import RetryPolicy
    delays = list(RetryPolicy(max_retries=3, backoff_seconds=2.0).delays())
    assert delays == [2.0, 8.0, 32.0]


def test_per_symbol_swallows_exceptions():
    from remote_data.fetcher.base import per_symbol

    def fn(s):
        if s == "BAD":
            raise ValueError("nope")
        return s

    assert per_symbol(["GOOD", "BAD", "ALSO_GOOD"], fn) == ["GOOD", "ALSO_GOOD"]