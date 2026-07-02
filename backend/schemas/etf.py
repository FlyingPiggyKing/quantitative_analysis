"""Pydantic models for the ETF ingest + read API.

The ingest models match the wire format emitted by the overseas pusher
(`remote_data/pusher/payload.py` + `remote_data/fetcher/etf_*.py`) so the
contract aligns with what is actually on the wire. The read models normalize
field names for the frontend.

Design note on partial-success validation: each batch variant keeps `records`
as `List[dict]` (not `List[<typed record]`) so a single malformed record does
not fail the whole batch. The dispatcher validates each record individually
and accumulates per-index errors.
"""
from __future__ import annotations

from typing import Annotated, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# All data types the pusher may send.
DataType = Literal[
    "etf_quote",
    "etf_fundamentals",
    "etf_holdings",
    "etf_sector_weights",
    "etf_performance",
    "etf_equity_holdings",
    "etf_esg",
    "etf_news",
]


# --- Per-type record models (used by the dispatcher for per-record validation) ---


class EtfQuoteRecord(BaseModel):
    symbol: str
    ts: str
    price: Optional[float] = None
    pre_market_price: Optional[float] = None
    post_market_price: Optional[float] = None
    volume: Optional[int] = None


class EtfFundamentalsRecord(BaseModel):
    symbol: str
    as_of: str
    pe: Optional[float] = None
    pb: Optional[float] = None
    dividend_yield: Optional[float] = None
    dividend_rate: Optional[float] = None


class HoldingItem(BaseModel):
    symbol: Optional[str] = None
    name: Optional[str] = None
    weight_pct: Optional[float] = None


class EtfHoldingsRecord(BaseModel):
    symbol: str
    as_of_date: str
    holdings: List[HoldingItem]


class SectorItem(BaseModel):
    sector: Optional[str] = None
    weight_pct: Optional[float] = None


class EtfSectorWeightsRecord(BaseModel):
    symbol: str
    as_of_date: str
    sectors: List[SectorItem]


# Performance uses wire-format field names (ytd_return, return_1y, ...) to match
# the actual pusher output (see remote_data/fetcher/etf_performance.py). The
# read API normalizes to short names per the etf-read-api spec.
class EtfPerformanceRecord(BaseModel):
    symbol: str
    as_of_date: str
    ytd_return: Optional[float] = None
    return_1y: Optional[float] = None
    return_3y: Optional[float] = None
    return_5y: Optional[float] = None
    return_10y: Optional[float] = None


class EquityHoldingItem(BaseModel):
    symbol: Optional[str] = None
    name: Optional[str] = None
    weight_pct: Optional[float] = None
    pe: Optional[float] = None
    pb: Optional[float] = None
    ps: Optional[float] = None


class EtfEquityHoldingsRecord(BaseModel):
    symbol: str
    as_of_date: str
    holdings: List[EquityHoldingItem]


class EtfEsgRecord(BaseModel):
    symbol: str
    as_of_date: str
    total_esg: Optional[float] = None
    environment: Optional[float] = None
    social: Optional[float] = None
    governance: Optional[float] = None


class EtfNewsRecord(BaseModel):
    url: str
    symbol: Optional[str] = None
    title: Optional[str] = None
    publisher: Optional[str] = None
    published_at: Optional[str] = None
    summary: Optional[str] = None


# Map data_type -> per-record validator. Used by the dispatcher.
RECORD_VALIDATORS = {
    "etf_quote": EtfQuoteRecord,
    "etf_fundamentals": EtfFundamentalsRecord,
    "etf_holdings": EtfHoldingsRecord,
    "etf_sector_weights": EtfSectorWeightsRecord,
    "etf_performance": EtfPerformanceRecord,
    "etf_equity_holdings": EtfEquityHoldingsRecord,
    "etf_esg": EtfEsgRecord,
    "etf_news": EtfNewsRecord,
}


# --- Ingest request: discriminated union on `data_type` ---


class _BatchEnvelope(BaseModel):
    """Shared shape for every batch variant. `records` is `List[dict]` so the
    dispatcher can validate each record individually (partial-success flow)."""

    batch_id: str
    records: List[dict]


class EtfQuoteBatch(_BatchEnvelope):
    data_type: Literal["etf_quote"] = "etf_quote"


class EtfFundamentalsBatch(_BatchEnvelope):
    data_type: Literal["etf_fundamentals"] = "etf_fundamentals"


class EtfHoldingsBatch(_BatchEnvelope):
    data_type: Literal["etf_holdings"] = "etf_holdings"


class EtfSectorWeightsBatch(_BatchEnvelope):
    data_type: Literal["etf_sector_weights"] = "etf_sector_weights"


class EtfPerformanceBatch(_BatchEnvelope):
    data_type: Literal["etf_performance"] = "etf_performance"


class EtfEquityHoldingsBatch(_BatchEnvelope):
    data_type: Literal["etf_equity_holdings"] = "etf_equity_holdings"


class EtfEsgBatch(_BatchEnvelope):
    data_type: Literal["etf_esg"] = "etf_esg"


class EtfNewsBatch(_BatchEnvelope):
    data_type: Literal["etf_news"] = "etf_news"


IngestRequest = Annotated[
    Union[
        EtfQuoteBatch,
        EtfFundamentalsBatch,
        EtfHoldingsBatch,
        EtfSectorWeightsBatch,
        EtfPerformanceBatch,
        EtfEquityHoldingsBatch,
        EtfEsgBatch,
        EtfNewsBatch,
    ],
    Field(discriminator="data_type"),
]


# --- Ingest response ---


class IngestError(BaseModel):
    index: int
    error: str


class IngestResponse(BaseModel):
    accepted: int
    rejected: int
    batch_id: str
    errors: Optional[List[IngestError]] = None


# --- Read response models ---


class QuoteRow(BaseModel):
    ts: str
    price: Optional[float] = None
    pre_market_price: Optional[float] = None
    post_market_price: Optional[float] = None
    volume: Optional[int] = None


class QuoteListResponse(BaseModel):
    symbol: str
    quotes: List[QuoteRow]


class FundamentalsResponse(BaseModel):
    symbol: str
    as_of: str
    pe: Optional[float] = None
    pb: Optional[float] = None
    dividend_yield: Optional[float] = None
    dividend_rate: Optional[float] = None


class HoldingsResponse(BaseModel):
    symbol: str
    as_of_date: str
    holdings: List[HoldingItem]


class SectorWeightsResponse(BaseModel):
    symbol: str
    as_of_date: str
    sectors: List[SectorItem]


class EquityHoldingsResponse(BaseModel):
    symbol: str
    as_of_date: str
    holdings: List[EquityHoldingItem]


class PerformanceResponse(BaseModel):
    symbol: str
    as_of_date: str
    ytd: Optional[float] = None
    one_year: Optional[float] = Field(None, alias="1y")
    three_year: Optional[float] = Field(None, alias="3y")
    five_year: Optional[float] = Field(None, alias="5y")
    ten_year: Optional[float] = Field(None, alias="10y")

    model_config = {"populate_by_name": True}


class EsgResponse(BaseModel):
    symbol: str
    as_of_date: str
    total_esg: Optional[float] = None
    environment: Optional[float] = None
    social: Optional[float] = None
    governance: Optional[float] = None


class NewsItem(BaseModel):
    url: str
    title: Optional[str] = None
    publisher: Optional[str] = None
    published_at: Optional[str] = None
    summary: Optional[str] = None


class NewsListResponse(BaseModel):
    symbol: str
    page: int
    page_size: int
    total: int
    news: List[NewsItem]


class SymbolsResponse(BaseModel):
    symbols: List[str]
