"""Stock API routes."""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from backend.services.akshare_service import AShareService, USStockService, HKStockService, _is_us_stock_symbol, _is_hk_stock_symbol, calculate_indicators

router = APIRouter(prefix="/api/stock", tags=["stock"])


def _split_by_market(symbols: List[str]) -> tuple[List[str], List[str], List[str]]:
    """Split symbols into A-share, US stock, and HK stock lists."""
    a_share = []
    us_stocks = []
    hk_stocks = []
    for s in symbols:
        if _is_hk_stock_symbol(s):
            hk_stocks.append(s)
        elif _is_us_stock_symbol(s):
            us_stocks.append(s)
        else:
            a_share.append(s)
    return a_share, us_stocks, hk_stocks


# Batch endpoints MUST be defined BEFORE /{symbol} to avoid route conflicts
@router.get("/batch/valuation")
async def get_batch_valuation(
    symbols: str = Query(..., description="Comma-separated stock symbols, e.g., 600938,601899,GOOGL,TSLA"),
    days: int = Query(default=30, ge=1, le=365)
):
    """Get daily valuation metrics for multiple stocks in a single request.

    Supports mixed A-share, US, and HK stock symbols. Reduces N+1 query problem to 1 request.
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        return {"results": [], "errors": [{"error": "No symbols provided"}]}

    a_share_symbols, us_symbols, hk_symbols = _split_by_market(symbol_list)

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

    # Fetch HK stock valuations
    if hk_symbols:
        hk_result = HKStockService.get_daily_basic_batch(hk_symbols, days)
        results.extend(hk_result.get("results", []))
        errors.extend(hk_result.get("errors", []))

    return {"results": results, "errors": errors}


@router.get("/batch/info")
async def get_batch_info(
    symbols: str = Query(..., description="Comma-separated stock symbols, e.g., 600938,601899,GOOGL,TSLA")
):
    """Get basic stock information for multiple stocks in a single request.

    Supports mixed A-share, US, and HK stock symbols. Reduces N+1 query problem to 1 request.
    """
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    if not symbol_list:
        return {"results": [], "errors": [{"error": "No symbols provided"}]}

    a_share_symbols, us_symbols, hk_symbols = _split_by_market(symbol_list)

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

    # Fetch HK stock info
    if hk_symbols:
        hk_result = HKStockService.get_stock_info_batch(hk_symbols)
        results.extend(hk_result.get("results", []))
        errors.extend(hk_result.get("errors", []))

    return {"results": results, "errors": errors}


@router.get("/sector-top-stocks")
async def get_sector_top_stocks(
    sector: str = Query(..., description="Sector name (e.g. 白酒)"),
    dates: str = Query(..., description="Comma-separated YYYY-MM-DD dates"),
    top_n: int = Query(default=5, ge=1, le=20)
):
    """Get top N stocks by main-force net inflow for a sector on given dates.

    Resolves the sector name to SW2021 index members, fetches per-stock money flow,
    and returns the top N companies ranked by net inflow (亿元) per date.
    """
    date_list = [d.strip() for d in dates.split(",") if d.strip()]
    return AShareService.get_sector_top_stocks(sector, date_list, top_n)


@router.get("/dragon-tiger-list")
async def get_dragon_tiger_list(days: int = Query(default=3, ge=1, le=10)):
    """Get Dragon Tiger List (机构龙虎榜) aggregated data.

    Returns top 5 net buy and top 5 net sell stocks from recent trading days (cumulative).
    This is a read-only endpoint that does NOT trigger AI analysis.
    """
    return AShareService.get_dragon_tiger_list(days)


@router.get("/sector-money-flow")
async def get_sector_money_flow(
    days: int = Query(default=5, ge=1, le=30),
    top_n: int = Query(default=6, ge=1, le=20)
):
    """Get sector-level money flow Sankey data.

    Returns top N sectors per day for the past several trading days,
    with net flow amounts, suitable for Sankey visualization.
    """
    return AShareService.get_sector_moneyflow(days=days, top_n=top_n)


@router.get("/company")
async def get_company_info(symbol: str = Query(..., description="6-digit A-share symbol, e.g., 601899")):
    """Get A-share listed-company basic info via Tushare stock_company.

    Returns shape ``{data: <row or null>, error: <str or null>}``.
    """
    if not (isinstance(symbol, str) and symbol.isdigit() and len(symbol) == 6):
        raise HTTPException(status_code=400, detail={"error": "A-share symbol required (6-digit numeric)"})
    return AShareService.get_company_info(symbol)


@router.get("/main-business")
async def get_main_business(
    symbol: str = Query(..., description="6-digit A-share symbol, e.g., 601899"),
    type: str = Query(default="P", description="P=product, D=region, I=industry"),
    period: Optional[str] = Query(default=None, description="Reporting period YYYYMMDD; default = latest"),
):
    """Get A-share main business composition via Tushare fina_mainbz (doc_id=81).

    Returns shape ``{ts_code, period, type, rows, source, updated_at}`` on success
    or ``{rows: []}`` when Tushare has no data. Cached 24h per (ts_code, type, period).
    """
    if not (isinstance(symbol, str) and symbol.isdigit() and len(symbol) == 6):
        raise HTTPException(status_code=400, detail={"error": "仅支持 A 股 6 位代码"})
    if type not in ("P", "D", "I"):
        raise HTTPException(status_code=400, detail={"error": f"type 必须是 P/D/I，当前: {type}"})
    if period is not None and (not period.isdigit() or len(period) != 8):
        raise HTTPException(status_code=400, detail={"error": "period 必须是 YYYYMMDD 格式"})
    try:
        return AShareService.get_main_business_composition(symbol, period=period, type=type)
    except Exception as e:
        raise HTTPException(status_code=502, detail={"error": "Tushare 数据源异常", "ts_code": _symbol_to_ts_code_safe(symbol), "detail": str(e)[:200]})


@router.get("/main-business/history")
async def get_main_business_history(
    symbol: str = Query(..., description="6-digit A-share symbol, e.g., 601899"),
    type: str = Query(default="P", description="P=product, D=region, I=industry"),
    top: int = Query(default=3, ge=1, le=10, description="Number of top series to keep; rest aggregated as '其他'"),
):
    """Get last 4 annual periods of by-product/by-region/by-industry data for cross-period view.

    Returns shape ``{ts_code, type, periods, series: [{item, values}], source, updated_at}``.
    """
    if not (isinstance(symbol, str) and symbol.isdigit() and len(symbol) == 6):
        raise HTTPException(status_code=400, detail={"error": "仅支持 A 股 6 位代码"})
    if type not in ("P", "D", "I"):
        raise HTTPException(status_code=400, detail={"error": f"type 必须是 P/D/I，当前: {type}"})
    try:
        return AShareService.get_main_business_history(symbol, type=type, top=top)
    except Exception as e:
        raise HTTPException(status_code=502, detail={"error": "Tushare 数据源异常", "ts_code": _symbol_to_ts_code_safe(symbol), "detail": str(e)[:200]})


@router.get("/main-business/has-distinct-industry")
async def get_has_distinct_industry(
    symbol: str = Query(..., description="6-digit A-share symbol"),
    period: Optional[str] = Query(default=None, description="Reporting period YYYYMMDD; default = latest"),
):
    """Whether the by-industry rows add items not present in by-product rows.

    Returns ``{has_distinct: bool, industry_items: [...]}``.
    """
    if not (isinstance(symbol, str) and symbol.isdigit() and len(symbol) == 6):
        raise HTTPException(status_code=400, detail={"error": "仅支持 A 股 6 位代码"})
    try:
        return AShareService.has_distinct_industry(symbol, period=period)
    except Exception as e:
        raise HTTPException(status_code=502, detail={"error": "Tushare 数据源异常", "detail": str(e)[:200]})


def _symbol_to_ts_code_safe(symbol: str) -> str:
    """Best-effort convert 6-digit symbol to ts_code; never raises."""
    from backend.services.akshare_service import _symbol_to_ts_code
    try:
        return _symbol_to_ts_code(symbol)
    except Exception:
        return symbol


@router.get("/{symbol}")
async def get_stock_info(symbol: str):
    """Get basic stock information."""
    if _is_hk_stock_symbol(symbol):
        return HKStockService.get_stock_info(symbol)
    elif _is_us_stock_symbol(symbol):
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
    if _is_hk_stock_symbol(symbol):
        return HKStockService.get_kline_data(symbol, days, period, adjust)
    elif _is_us_stock_symbol(symbol):
        return USStockService.get_kline_data(symbol, days, period, adjust)
    else:
        return AShareService.get_kline_data(symbol, days, period, adjust)


@router.get("/{symbol}/realtime")
async def get_realtime(symbol: str):
    """Get real-time quote for a stock."""
    if _is_hk_stock_symbol(symbol):
        return HKStockService.get_realtime_quote(symbol)
    elif _is_us_stock_symbol(symbol):
        return USStockService.get_realtime_quote(symbol)
    else:
        return AShareService.get_realtime_quote(symbol)


@router.get("/{symbol}/indicators")
async def get_indicators(symbol: str, days: int = Query(default=100, ge=30, le=500)):
    """Get technical indicators (MACD, RSI, MA) for a stock."""
    if _is_hk_stock_symbol(symbol):
        kline_result = HKStockService.get_kline_data(symbol, days)
    elif _is_us_stock_symbol(symbol):
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
    if _is_hk_stock_symbol(symbol):
        return HKStockService.get_daily_basic(symbol, days)
    elif _is_us_stock_symbol(symbol):
        return USStockService.get_daily_basic(symbol, days)
    else:
        return AShareService.get_daily_basic(symbol, days)


@router.get("/{symbol}/fundamentals")
async def get_financial_fundamentals(symbol: str):
    """Get quarterly financial fundamentals (EPS, ROE, profit margins, growth rates) for A-share stocks.

    Returns "暂不适用" error for HK and US stocks (FutuAPI does not provide financial fundamentals).
    """
    if _is_hk_stock_symbol(symbol) or _is_us_stock_symbol(symbol):
        return {"symbol": symbol, "error": "暂不适用", "data": None}
    return AShareService.get_financial_fundamentals(symbol)


@router.get("/{symbol}/moneyflow")
async def get_moneyflow(symbol: str, days: int = Query(default=30, ge=1, le=365)):
    """Get main force net inflow (money flow) for a stock.

    Routes to appropriate service based on symbol:
    - A-share (SH/SZ prefix or 6-digit code): Tushare moneyflow_ths
    - HK stock (4-5 digit code): Futu get_capital_flow
    - US stock (.US suffix or regular symbols): Futu get_capital_flow
    """
    if _is_hk_stock_symbol(symbol):
        return HKStockService.get_moneyflow(symbol, days)
    elif _is_us_stock_symbol(symbol):
        return USStockService.get_moneyflow(symbol, days)
    else:
        return AShareService.get_moneyflow(symbol, days)
