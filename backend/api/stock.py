"""Stock API routes."""
from fastapi import APIRouter, Query
from typing import List
from backend.services.akshare_service import AkshareService

router = APIRouter(prefix="/api/stock", tags=["stock"])


# Batch endpoints MUST be defined BEFORE /{symbol} to avoid route conflicts
@router.get("/batch/valuation")
async def get_batch_valuation(
    symbols: str = Query(..., description="Comma-separated stock symbols, e.g., 600938,601899,300750"),
    days: int = Query(default=30, ge=1, le=365)
):
    """Get daily valuation metrics for multiple stocks in a single request.

    Reduces N+1 query problem to 1 request.
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        return {"results": [], "errors": [{"error": "No symbols provided"}]}
    return AkshareService.get_daily_basic_batch(symbol_list, days)


@router.get("/batch/info")
async def get_batch_info(
    symbols: str = Query(..., description="Comma-separated stock symbols, e.g., 600938,601899,300750")
):
    """Get basic stock information for multiple stocks in a single request.

    Reduces N+1 query problem to 1 request.
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        return {"results": [], "errors": [{"error": "No symbols provided"}]}
    return AkshareService.get_stock_info_batch(symbol_list)


@router.get("/{symbol}")
async def get_stock_info(symbol: str):
    """Get basic stock information."""
    return AkshareService.get_stock_info(symbol)


@router.get("/{symbol}/kline")
async def get_kline(
    symbol: str,
    days: int = Query(default=100, ge=1, le=500),
    period: str = Query(default="daily", pattern="^(daily|weekly|monthly)$"),
    adjust: str = Query(default="qfq", pattern="^(qfq|hfq|no)$")
):
    """Get K-line data for a stock."""
    return AkshareService.get_kline_data(symbol, days, period, adjust)


@router.get("/{symbol}/realtime")
async def get_realtime(symbol: str):
    """Get real-time quote for a stock."""
    return AkshareService.get_realtime_quote(symbol)


@router.get("/{symbol}/indicators")
async def get_indicators(symbol: str, days: int = Query(default=100, ge=30, le=500)):
    """Get technical indicators (MACD, RSI, MA) for a stock."""
    kline_result = AkshareService.get_kline_data(symbol, days)
    if "error" in kline_result:
        return kline_result

    indicators = AkshareService.calculate_indicators(kline_result["data"])
    return {
        "symbol": symbol,
        "indicators": indicators
    }


@router.get("/{symbol}/valuation")
async def get_valuation(symbol: str, days: int = Query(default=30, ge=1, le=365)):
    """Get daily valuation metrics (PE TTM, PB, turnover rate, market cap) for a stock."""
    return AkshareService.get_daily_basic(symbol, days)
