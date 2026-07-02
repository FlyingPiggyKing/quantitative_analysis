"""GET endpoints under /api/etf for the frontend.

All endpoints are read-only, NOT protected by HMAC (per the spec), and not
rate-limited. They return 404 with `{"detail": "no <type> for <symbol>"}`
when no data exists for the requested symbol.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.services import etf_service

router = APIRouter(prefix="/api/etf", tags=["etf-read"])


def _not_found(type_name: str, symbol: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"no {type_name} for {symbol}")


@router.get("/symbols")
async def list_symbols() -> dict:
    return {"symbols": etf_service.list_symbols()}


@router.get("/quote/{symbol}")
async def get_quote(
    symbol: str,
    limit: int = Query(default=480, ge=1, le=5000),
) -> dict:
    quotes = etf_service.get_latest_quote(symbol, limit)
    if not quotes:
        raise _not_found("quote", symbol)
    return {"symbol": symbol, "quotes": quotes}


@router.get("/fundamentals/{symbol}")
async def get_fundamentals(symbol: str) -> dict:
    row = etf_service.get_fundamentals(symbol)
    if not row:
        raise _not_found("fundamentals", symbol)
    return {"symbol": symbol, **row}


@router.get("/holdings/{symbol}")
async def get_holdings(symbol: str) -> dict:
    row = etf_service.get_holdings(symbol)
    if not row:
        raise _not_found("holdings", symbol)
    return row


@router.get("/sector-weights/{symbol}")
async def get_sector_weights(symbol: str) -> dict:
    row = etf_service.get_sector_weights(symbol)
    if not row:
        raise _not_found("sector-weights", symbol)
    return row


@router.get("/equity-holdings/{symbol}")
async def get_equity_holdings(symbol: str) -> dict:
    row = etf_service.get_equity_holdings(symbol)
    if not row:
        raise _not_found("equity-holdings", symbol)
    return row


@router.get("/performance/{symbol}")
async def get_performance(symbol: str) -> dict:
    row = etf_service.get_performance(symbol)
    if not row:
        raise _not_found("performance", symbol)
    return row


@router.get("/esg/{symbol}")
async def get_esg(symbol: str) -> dict:
    row = etf_service.get_esg(symbol)
    if not row:
        raise _not_found("esg", symbol)
    return row


@router.get("/news/{symbol}")
async def get_news(
    symbol: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    result = etf_service.get_news(symbol, page, page_size)
    if result["total"] == 0:
        raise _not_found("news", symbol)
    return {
        "symbol": symbol,
        "page": page,
        "page_size": page_size,
        "total": result["total"],
        "news": result["items"],
    }
