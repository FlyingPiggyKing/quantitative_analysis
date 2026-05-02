"""Stock API routes."""
from fastapi import APIRouter, Query
from typing import List
from backend.services.akshare_service import AShareService, USStockService, _is_us_stock_symbol, calculate_indicators

router = APIRouter(prefix="/api/stock", tags=["stock"])


def _split_by_market(symbols: List[str]) -> tuple[List[str], List[str]]:
    """Split symbols into A-share and US stock lists."""
    a_share = []
    us_stocks = []
    for s in symbols:
        if _is_us_stock_symbol(s):
            us_stocks.append(s)
        else:
            a_share.append(s)
    return a_share, us_stocks


# Batch endpoints MUST be defined BEFORE /{symbol} to avoid route conflicts
@router.get("/batch/valuation")
async def get_batch_valuation(
    symbols: str = Query(..., description="Comma-separated stock symbols, e.g., 600938,601899,GOOGL,TSLA"),
    days: int = Query(default=30, ge=1, le=365)
):
    """Get daily valuation metrics for multiple stocks in a single request.

    Supports mixed A-share and US stock symbols. Reduces N+1 query problem to 1 request.
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        return {"results": [], "errors": [{"error": "No symbols provided"}]}

    a_share_symbols, us_symbols = _split_by_market(symbol_list)

    results = []
    errors = []

    # Fetch A-share valuations
    if a_share_symbols:
        a_result = AShareService.get_daily_basic_batch(a_share_symbols, days)
        results.extend(a_result.get("results", []))
        errors.extend(a_result.get("errors", []))

    # Fetch US stock valuations
    if us_symbols:
        us_result = USStockService.get_daily_basic_batch(us_symbols, days)
        results.extend(us_result.get("results", []))
        errors.extend(us_result.get("errors", []))

    return {"results": results, "errors": errors}


@router.get("/batch/info")
async def get_batch_info(
    symbols: str = Query(..., description="Comma-separated stock symbols, e.g., 600938,601899,GOOGL,TSLA")
):
    """Get basic stock information for multiple stocks in a single request.

    Supports mixed A-share and US stock symbols. Reduces N+1 query problem to 1 request.
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        return {"results": [], "errors": [{"error": "No symbols provided"}]}

    a_share_symbols, us_symbols = _split_by_market(symbol_list)

    results = []
    errors = []

    # Fetch A-share info
    if a_share_symbols:
        a_result = AShareService.get_stock_info_batch(a_share_symbols)
        results.extend(a_result.get("results", []))
        errors.extend(a_result.get("errors", []))

    # Fetch US stock info
    if us_symbols:
        us_result = USStockService.get_stock_info_batch(us_symbols)
        results.extend(us_result.get("results", []))
        errors.extend(us_result.get("errors", []))

    return {"results": results, "errors": errors}


@router.get("/{symbol}")
async def get_stock_info(symbol: str):
    """Get basic stock information."""
    if _is_us_stock_symbol(symbol):
        return USStockService.get_stock_info(symbol)
    else:
        return AShareService.get_stock_info(symbol)


@router.get("/{symbol}/kline")
async def get_kline(
    symbol: str,
    days: int = Query(default=100, ge=1, le=500),
    period: str = Query(default="daily", pattern="^(daily|weekly|monthly)$"),
    adjust: str = Query(default="qfq", pattern="^(qfq|hfq|no)$")
):
    """Get K-line data for a stock."""
    if _is_us_stock_symbol(symbol):
        return USStockService.get_kline_data(symbol, days, period, adjust)
    else:
        return AShareService.get_kline_data(symbol, days, period, adjust)


@router.get("/{symbol}/realtime")
async def get_realtime(symbol: str):
    """Get real-time quote for a stock."""
    if _is_us_stock_symbol(symbol):
        return USStockService.get_realtime_quote(symbol)
    else:
        return AShareService.get_realtime_quote(symbol)


@router.get("/{symbol}/indicators")
async def get_indicators(symbol: str, days: int = Query(default=100, ge=30, le=500)):
    """Get technical indicators (MACD, RSI, MA) for a stock."""
    if _is_us_stock_symbol(symbol):
        kline_result = USStockService.get_kline_data(symbol, days)
    else:
        kline_result = AShareService.get_kline_data(symbol, days)

    if "error" in kline_result:
        return kline_result

    indicators = calculate_indicators(kline_result["data"])
    return {
        "symbol": symbol,
        "indicators": indicators
    }


@router.get("/{symbol}/valuation")
async def get_valuation(symbol: str, days: int = Query(default=30, ge=1, le=365)):
    """Get daily valuation metrics (PE TTM, PB, turnover rate, market cap) for a stock."""
    if _is_us_stock_symbol(symbol):
        return USStockService.get_daily_basic(symbol, days)
    else:
        return AShareService.get_daily_basic(symbol, days)
