"""Stock API routes."""
from fastapi import APIRouter, Query
from backend.services.akshare_service import AkshareService

router = APIRouter(prefix="/api/stock", tags=["stock"])


@router.get("/{symbol}")
async def get_stock_info(symbol: str):
    """Get basic stock information."""
    return AkshareService.get_stock_info(symbol)


@router.get("/{symbol}/kline")
async def get_kline(
    symbol: str,
    days: int = Query(default=100, ge=1, le=500),
    period: str = Query(default="daily", regex="^(daily|weekly|monthly)$"),
    adjust: str = Query(default="qfq", regex="^(qfq|hfq|no)$")
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
async def get_valuation(symbol: str, days: int = Query(default=100, ge=30, le=500)):
    """Get PE, PB, and turnover rate valuation metrics for a stock."""
    return AkshareService.get_valuation_data(symbol, days)
