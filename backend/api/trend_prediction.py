"""Trend prediction API routes."""
import time
import logging
from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel
from typing import List, Optional

from backend.services.trend_prediction_service import TrendPredictionService
from backend.services.watchlist_service import WatchlistService
from backend.services.stock_trend_agent import analyze_stock_trend
from backend.api.auth import get_current_user
from backend.services.task_queue import (
    submit_analysis_task,
    get_task_status,
    TaskStatus,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trend-predictions", tags=["trend-predictions"])


class PredictionResponse(BaseModel):
    symbol: str
    name: str
    trend_direction: str
    confidence: int
    summary: str
    analyzed_at: str
    is_fallback: bool = False
    情绪分析: Optional[dict] = None
    技术分析: Optional[dict] = None
    趋势判断: Optional[dict] = None


class BatchAnalysisResponse(BaseModel):
    analyzed: int
    failed: int
    results: List[PredictionResponse]


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: str
    current: int
    total: int
    results: Optional[List[PredictionResponse]] = None
    error: Optional[str] = None


class BatchAsyncResponse(BaseModel):
    task_id: str
    status: str
    message: str


class BatchAnalysisRequest(BaseModel):
    force: bool = False


class BatchAsyncRequest(BaseModel):
    force: bool = False


@router.get("", response_model=List[PredictionResponse])
async def get_all_predictions():
    """Get all latest predictions for analyzed stocks."""
    predictions = TrendPredictionService.get_all_latest_predictions()
    return predictions


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status_endpoint(task_id: str):
    """Get the status of a batch analysis task."""
    task = get_task_status(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        task_id=task.task_id,
        status=task.status.value,
        progress=task.progress,
        current=task.current,
        total=task.total,
        results=task.results if task.status == TaskStatus.COMPLETED else None,
        error=task.error,
    )


@router.get("/{symbol}", response_model=PredictionResponse)
async def get_prediction(
    symbol: str,
    force: bool = False,
    authorization: Optional[str] = Header(None),
):
    """Get the latest prediction for a specific stock.

    If force=false (default) and a valid cached result exists for today,
    returns the cached result without re-analysis.
    If force=true, performs fresh analysis regardless of cache.
    Rate limit: only one force analysis per user per stock per hour.
    Requires authentication for force=true.
    """
    user_id = None
    if force:
        # Auth required for force analysis
        from backend.api.auth import get_current_user
        current_user = get_current_user(authorization)
        user_id = current_user.get("user_id")

        # Check rate limit
        if TrendPredictionService.check_rate_limit(user_id, symbol):
            remaining = TrendPredictionService.get_rate_limit_remaining_seconds(user_id, symbol)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": remaining,
                },
                headers={"retry_after": str(remaining)},
            )
        # Record this trigger
        TrendPredictionService.record_trigger(user_id, symbol)

    if not force:
        cached = TrendPredictionService.get_today_prediction(symbol)
        if cached:
            logger.info(f"Returning cached prediction for {symbol} (force=False)")
            cached["is_fallback"] = False
            return cached
        # No prediction for today — fall back to most recent prediction
        latest = TrendPredictionService.get_latest_prediction(symbol)
        if latest:
            logger.info(f"No today's prediction for {symbol}, falling back to latest from {latest.get('analyzed_at')}")
            latest["is_fallback"] = True
            return latest
        # No predictions at all
        raise HTTPException(
            status_code=404,
            detail="No prediction available. Please login and use force analysis.",
        )

    # Look up name from watchlist first, fallback to stock info API
    name = symbol
    try:
        from backend.services.watchlist_service import WatchlistService
        watchlist = WatchlistService.get_watchlist(page=1, page_size=100)
        for stock in watchlist.get("items", []):
            if stock["symbol"] == symbol:
                name = stock["name"]
                break
    except Exception:
        pass

    # If name still equals symbol, try to get from stock info API
    if name == symbol:
        try:
            from backend.services.akshare_service import AkshareService
            stock_info = AkshareService.get_stock_info(symbol)
            if stock_info and "name" in stock_info and stock_info["name"]:
                name = stock_info["name"]
        except Exception:
            pass

    # Run fresh analysis
    prediction = analyze_stock_trend(symbol, name)

    # Save prediction with extended analysis
    extended_analysis = None
    if prediction.get("情绪分析") or prediction.get("技术分析") or prediction.get("趋势判断"):
        extended_analysis = {
            "情绪分析": prediction.get("情绪分析"),
            "技术分析": prediction.get("技术分析"),
            "趋势判断": prediction.get("趋势判断"),
        }
    saved = TrendPredictionService.save_prediction(
        symbol=symbol,
        name=name,
        trend_direction=prediction.get("trend_direction", "neutral"),
        confidence=prediction.get("confidence", 0),
        summary=prediction.get("summary", ""),
        extended_analysis=extended_analysis,
    )
    saved["is_fallback"] = False
    return saved


@router.post("/batch", response_model=BatchAnalysisResponse)
async def batch_analyze(request: BatchAnalysisRequest = None):
    """Run trend analysis for all stocks in the watchlist.

    If force=false (default), skips stocks that already have a valid cached result today.
    If force=true, analyzes all stocks regardless of cache.
    """
    force = request.force if request else False
    logger.info(f"Starting batch analysis for watchlist (force={force})")
    # Get all stocks from watchlist
    watchlist_result = WatchlistService.get_watchlist(page=1, page_size=100)
    stocks = watchlist_result.get("items", [])
    logger.info(f"Found {len(stocks)} stocks in watchlist")

    if not stocks:
        return BatchAnalysisResponse(analyzed=0, failed=0, results=[])

    results = []
    analyzed_count = 0
    failed_count = 0

    for stock in stocks:
        symbol = stock["symbol"]
        name = stock["name"]

        # Check cache if not forcing
        if not force:
            cached = TrendPredictionService.get_today_prediction(symbol)
            if cached:
                logger.info(f"Skipping {name} ({symbol}) - cached result exists")
                results.append(cached)
                continue

        logger.info(f"Analyzing stock: {name} ({symbol})")

        try:
            # Run analysis
            logger.info(f"Calling analyze_stock_trend for {symbol}...")
            prediction = analyze_stock_trend(symbol, name)
            logger.info(f"Analysis complete for {symbol}: {prediction.get('trend_direction')}")

            # Save prediction with extended analysis
            extended_analysis = None
            if prediction.get("情绪分析") or prediction.get("技术分析") or prediction.get("趋势判断"):
                extended_analysis = {
                    "情绪分析": prediction.get("情绪分析"),
                    "技术分析": prediction.get("技术分析"),
                    "趋势判断": prediction.get("趋势判断"),
                }
            saved = TrendPredictionService.save_prediction(
                symbol=symbol,
                name=name,
                trend_direction=prediction.get("trend_direction", "neutral"),
                confidence=prediction.get("confidence", 0),
                summary=prediction.get("summary", ""),
                extended_analysis=extended_analysis,
            )
            results.append(saved)
            analyzed_count += 1
            logger.info(f"Saved prediction for {symbol}")

            # Small delay to avoid rate limiting
            time.sleep(1)

        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to analyze {symbol}: {e}")

    return BatchAnalysisResponse(
        analyzed=analyzed_count,
        failed=failed_count,
        results=results,
    )


@router.post("/batch-async", response_model=BatchAsyncResponse)
async def batch_analyze_async(request: BatchAsyncRequest = None, current_user: dict = Depends(get_current_user)):
    """Submit batch analysis to run in background without blocking.

    If force=false (default), skips stocks that already have a valid cached result today.
    If force=true, analyzes all stocks regardless of cache.
    Returns immediately with a task_id that can be used to poll for status.
    """
    force = request.force if request else False
    logger.info(f"Submitting batch analysis task to background queue (force={force})")

    watchlist_result = WatchlistService.get_watchlist(user_id=current_user["user_id"], page=1, page_size=100)
    stocks = watchlist_result.get("items", [])
    logger.info(f"Found {len(stocks)} stocks in watchlist for async analysis")

    if not stocks:
        return BatchAsyncResponse(
            task_id="",
            status="completed",
            message="No stocks in watchlist",
        )

    task_id = submit_analysis_task(stocks, force=force)
    logger.info(f"Submitted analysis task {task_id} for {len(stocks)} stocks (force={force})")

    return BatchAsyncResponse(
        task_id=task_id,
        status="pending",
        message=f"Analysis queued for {len(stocks)} stocks (force={force})",
    )
