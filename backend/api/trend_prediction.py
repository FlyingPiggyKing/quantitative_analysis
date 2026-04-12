"""Trend prediction API routes."""
import time
import logging
from fastapi import APIRouter, HTTPException, Depends
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
async def get_prediction(symbol: str):
    """Get the latest prediction for a specific stock."""
    prediction = TrendPredictionService.get_latest_prediction(symbol)
    if prediction is None:
        raise HTTPException(status_code=404, detail="No prediction found for this stock")
    return prediction


@router.post("/batch", response_model=BatchAnalysisResponse)
async def batch_analyze():
    """Run trend analysis for all stocks in the watchlist."""
    logger.info("Starting batch analysis for watchlist")
    # Get all stocks from watchlist
    watchlist_result = WatchlistService.get_watchlist(page=1, page_size=100)
    stocks = watchlist_result.get("items", [])
    logger.info(f"Found {len(stocks)} stocks in watchlist")

    if not stocks:
        return BatchAnalysisResponse(analyzed=0, failed=0, results=[])

    results = []
    failed = 0

    for stock in stocks:
        symbol = stock["symbol"]
        name = stock["name"]
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
            logger.info(f"Saved prediction for {symbol}")

            # Small delay to avoid rate limiting
            time.sleep(1)

        except Exception as e:
            failed += 1
            logger.error(f"Failed to analyze {symbol}: {e}")

    return BatchAnalysisResponse(
        analyzed=len(results),
        failed=failed,
        results=results,
    )


@router.post("/batch-async", response_model=BatchAsyncResponse)
async def batch_analyze_async(current_user: dict = Depends(get_current_user)):
    """Submit batch analysis to run in background without blocking.

    Returns immediately with a task_id that can be used to poll for status.
    """
    logger.info("Submitting batch analysis task to background queue")

    watchlist_result = WatchlistService.get_watchlist(user_id=current_user["user_id"], page=1, page_size=100)
    stocks = watchlist_result.get("items", [])
    logger.info(f"Found {len(stocks)} stocks in watchlist for async analysis")

    if not stocks:
        return BatchAsyncResponse(
            task_id="",
            status="completed",
            message="No stocks in watchlist",
        )

    task_id = submit_analysis_task(stocks)
    logger.info(f"Submitted analysis task {task_id} for {len(stocks)} stocks")

    return BatchAsyncResponse(
        task_id=task_id,
        status="pending",
        message=f"Analysis queued for {len(stocks)} stocks",
    )
