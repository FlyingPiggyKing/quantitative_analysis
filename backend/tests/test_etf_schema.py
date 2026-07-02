"""Schema validation tests.

Each per-type record model must reject missing required fields and wrong
types. The discriminated union must accept every supported data_type and
reject unknown ones.
"""
from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from backend.schemas.etf import (
    EtfEquityHoldingsBatch,
    EtfEsgBatch,
    EtfFundamentalsBatch,
    EtfFundamentalsRecord,
    EtfHoldingsBatch,
    EtfHoldingsRecord,
    EtfNewsBatch,
    EtfNewsRecord,
    EtfPerformanceBatch,
    EtfPerformanceRecord,
    EtfQuoteBatch,
    EtfQuoteRecord,
    EtfSectorWeightsBatch,
    IngestRequest,
)


@pytest.fixture
def adapter() -> TypeAdapter:
    return TypeAdapter(IngestRequest)


class TestPerRecordValidation:
    def test_quote_requires_symbol_and_ts(self):
        with pytest.raises(ValidationError):
            EtfQuoteRecord.model_validate({"ts": "2026-06-29T03:14:00Z"})
        with pytest.raises(ValidationError):
            EtfQuoteRecord.model_validate({"symbol": "QQQ"})

    def test_quote_wrong_field_type(self):
        with pytest.raises(ValidationError):
            EtfQuoteRecord.model_validate(
                {"symbol": "QQQ", "ts": "2026-06-29T03:14:00Z", "price": "not-a-number"}
            )

    def test_fundamentals_requires_symbol_and_as_of(self):
        with pytest.raises(ValidationError):
            EtfFundamentalsRecord.model_validate({"pe": 32.4})
        with pytest.raises(ValidationError):
            EtfFundamentalsRecord.model_validate({"symbol": "QQQ"})

    def test_holdings_requires_arrays(self):
        with pytest.raises(ValidationError):
            EtfHoldingsRecord.model_validate({"symbol": "QQQ", "as_of_date": "2026-06-29"})
        # holdings must be a list, not a string
        with pytest.raises(ValidationError):
            EtfHoldingsRecord.model_validate(
                {"symbol": "QQQ", "as_of_date": "2026-06-29", "holdings": "not-a-list"}
            )

    def test_performance_uses_wire_format_field_names(self):
        # Wire format from remote_data/fetcher/etf_performance.py uses
        # ytd_return, return_1y, return_3y, return_5y, return_10y. Short
        # names (ytd, 1y, ...) would be invalid here.
        rec = EtfPerformanceRecord.model_validate(
            {
                "symbol": "QQQ",
                "as_of_date": "2026-06-29",
                "ytd_return": 0.12,
                "return_1y": 0.25,
                "return_3y": 0.40,
                "return_5y": 0.95,
                "return_10y": 4.10,
            }
        )
        assert rec.return_1y == 0.25

    def test_news_requires_url(self):
        with pytest.raises(ValidationError):
            EtfNewsRecord.model_validate({"title": "Headline"})


class TestIngestRequestDiscriminatedUnion:
    def test_accepts_each_known_data_type(self, adapter):
        for dt, body in [
            (
                "etf_quote",
                {
                    "data_type": "etf_quote",
                    "batch_id": "b1",
                    "records": [{"symbol": "QQQ", "ts": "2026-06-29T03:14:00Z", "price": 100.0}],
                },
            ),
            (
                "etf_fundamentals",
                {
                    "data_type": "etf_fundamentals",
                    "batch_id": "b2",
                    "records": [{"symbol": "QQQ", "as_of": "2026-06-29", "pe": 32.4}],
                },
            ),
            (
                "etf_holdings",
                {
                    "data_type": "etf_holdings",
                    "batch_id": "b3",
                    "records": [
                        {
                            "symbol": "QQQ",
                            "as_of_date": "2026-06-29",
                            "holdings": [{"symbol": "AAPL", "name": "Apple", "weight_pct": 5.0}],
                        }
                    ],
                },
            ),
            (
                "etf_sector_weights",
                {
                    "data_type": "etf_sector_weights",
                    "batch_id": "b4",
                    "records": [
                        {
                            "symbol": "QQQ",
                            "as_of_date": "2026-06-29",
                            "sectors": [{"sector": "Tech", "weight_pct": 30.0}],
                        }
                    ],
                },
            ),
            (
                "etf_performance",
                {
                    "data_type": "etf_performance",
                    "batch_id": "b5",
                    "records": [
                        {
                            "symbol": "QQQ",
                            "as_of_date": "2026-06-29",
                            "ytd_return": 0.12,
                            "return_1y": 0.25,
                        }
                    ],
                },
            ),
            (
                "etf_equity_holdings",
                {
                    "data_type": "etf_equity_holdings",
                    "batch_id": "b6",
                    "records": [
                        {
                            "symbol": "QQQ",
                            "as_of_date": "2026-06-29",
                            "holdings": [{"symbol": "AAPL", "pe": 28.0, "pb": 5.0}],
                        }
                    ],
                },
            ),
            (
                "etf_esg",
                {
                    "data_type": "etf_esg",
                    "batch_id": "b7",
                    "records": [
                        {
                            "symbol": "QQQ",
                            "as_of_date": "2026-06-29",
                            "total_esg": 18.2,
                            "environment": 5.0,
                        }
                    ],
                },
            ),
            (
                "etf_news",
                {
                    "data_type": "etf_news",
                    "batch_id": "b8",
                    "records": [{"url": "https://example.com/x", "symbol": "QQQ", "title": "T"}],
                },
            ),
        ]:
            parsed = adapter.validate_python(body)
            assert parsed.data_type == dt

    def test_rejects_unknown_data_type(self, adapter):
        with pytest.raises(ValidationError):
            adapter.validate_python(
                {
                    "data_type": "etf_kline",
                    "batch_id": "b",
                    "records": [],
                }
            )

    def test_missing_batch_id(self, adapter):
        with pytest.raises(ValidationError):
            adapter.validate_python(
                {"data_type": "etf_quote", "records": [{"symbol": "QQQ", "ts": "x"}]}
            )
